"""Tkinter GUI for the HP 34401A driver.

This GUI intentionally lives outside the core driver package so the
production driver can be imported without importing UI code.

The module is import-safe: tkinter is imported lazily by ``main()`` so normal
package imports, tests, and headless CLI use do not require a display server.

UI concept: a familiar bench-DMM layout with a large numeric display, left-side
connection/status controls, central measurement controls, bottom trend plot,
logging panel, and raw-SCPI service console.  All instrument I/O runs on a
worker thread so the GUI remains responsive during slow NPLC measurements,
self-tests, serial timeouts, or recovery attempts.
"""

from __future__ import annotations

# Support both installed package use and direct execution, e.g.
#   python hp34401a_gui/app.py
# from a source checkout. This avoids relative-import failures in IDEs.
import sys
from pathlib import Path as _BootstrapPath

if __package__ in (None, ""):
    _project_root = _BootstrapPath(__file__).resolve().parents[1]
    if str(_project_root) not in sys.path:
        sys.path.insert(0, str(_project_root))

import csv
import datetime as _dt
import queue
import threading
import time
from pathlib import Path
from typing import Any, Callable

from hp34401a_dmm.config import DriverConfig, SerialRs232Config, StabilityProfile, VisaGpibConfig
from hp34401a_dmm.driver import Hp34401A
from hp34401a_dmm.enums import AcFilterHz, AutoRange, Nplc
from hp34401a_dmm.errors import Hp34401AError
from hp34401a_dmm.measurement import MeasurementReading


NPLC_VALUES = {str(n.value).rstrip("0").rstrip("."): n for n in Nplc}
RANGE_PRESETS: dict[str, list[str]] = {
    "DC Voltage": ["AUTO", "0.1", "1", "10", "100", "1000"],
    "AC Voltage": ["AUTO", "0.1", "1", "10", "100", "750"],
    "DC Current": ["AUTO", "0.01", "0.1", "1", "3"],
    "Resistance 2W": ["AUTO", "100", "1000", "10000", "100000", "1000000", "10000000", "100000000"],
    "Resistance 4W": ["AUTO", "100", "1000", "10000", "100000", "1000000", "10000000", "100000000"],
}


class _AppState:
    def __init__(self) -> None:
        self.driver: Hp34401A | None = None
        self.continuous_stop = threading.Event()
        self.worker_lock = threading.Lock()
        self.connected = False
        self.readings: list[MeasurementReading] = []


def _parse_range(token: str) -> float | AutoRange:
    token = token.strip().upper()
    if token in ("", "AUTO"):
        return AutoRange.AUTO
    if token == "DEF":
        return AutoRange.DEF
    if token == "MIN":
        return AutoRange.MIN
    if token == "MAX":
        return AutoRange.MAX
    return float(token)


def _parse_nplc(token: str) -> Nplc:
    try:
        value = float(token)
    except ValueError as exc:
        raise ValueError(f"Invalid NPLC value: {token!r}") from exc
    return min(list(Nplc), key=lambda n: abs(n.value - value))


def _parse_ac_filter(token: str) -> AcFilterHz:
    value = int(float(token))
    for f in AcFilterHz:
        if f.value == value:
            return f
    raise ValueError("AC filter must be 3, 20, or 200 Hz")


def _normalize_visa_resource(token: str) -> str:
    """Return a raw VISA resource from a GUI combobox value.

    The GUI currently stores raw VISA resource names directly, but accepting
    values formatted as ``RESOURCE | description`` keeps the field tolerant of
    future display improvements and user-pasted text.
    """
    return token.strip().split(" | ", 1)[0].strip()


def _list_visa_resources() -> list[str]:
    """List VISA resources available on this PC.

    This is deliberately a discovery-only operation: it does not open the
    instruments and does not send ``*IDN?``. Probing every resource can disturb
    other instruments in a production rack. The selected resource can be
    identified safely with the GUI's Identify button after connection.
    """
    try:
        import pyvisa  # type: ignore[import-not-found]
    except ImportError as exc:
        raise Hp34401AError(
            "pyvisa is not installed. Install the VISA extra or use the standalone build "
            "with VISA support: pip install -e .[visa]"
        ) from exc

    rm = None
    try:
        rm = pyvisa.ResourceManager()
        resources = [str(r) for r in rm.list_resources()]
    except Exception as exc:  # noqa: BLE001 - normalize optional backend failures for GUI
        raise Hp34401AError(f"Could not list VISA resources: {exc}") from exc
    finally:
        if rm is not None:
            try:
                rm.close()
            except Exception:
                pass

    # Prefer real VISA instrument resources but fall back to all resources so
    # serial-ASRL or unusual adapter names are still visible to the operator.
    instruments = [r for r in resources if "::INSTR" in r.upper()]
    return sorted(instruments or resources)


def _reading_to_row(reading: MeasurementReading, source: str) -> dict[str, Any]:
    return {
        "timestamp_utc": reading.timestamp_utc.isoformat(),
        "source": source,
        "function": reading.function.name,
        "value": reading.value,
        "unit": reading.unit,
        "is_overload": reading.is_overload,
        "is_valid": reading.is_valid,
        "raw": reading.raw,
        "nplc": reading.nplc,
        "aperture_s": reading.aperture_s,
        "was_retried": reading.was_retried,
        "retry_count": reading.retry_count,
        "reconnect_count": reading.reconnect_count,
        "recovery_actions": ";".join(reading.recovery_actions),
    }


def _append_csv(path: Path, reading: MeasurementReading, source: str) -> None:
    row = _reading_to_row(reading, source)
    exists = path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if not exists:
            writer.writeheader()
        writer.writerow(row)
        f.flush()


def main() -> int:
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk
    except Exception as exc:  # pragma: no cover - environment dependent
        print(f"Tkinter GUI is not available in this Python environment: {exc}")
        return 2

    class DmmGuiApp:
        def __init__(self, root: tk.Tk) -> None:
            self.root = root
            self.root.title("HP 34401A Production DMM")
            self.root.geometry("1180x760")
            self.state = _AppState()
            self.events: queue.Queue[tuple[str, Any]] = queue.Queue()

            self.transport_var = tk.StringVar(value="VISA GPIB")
            self.serial_port_var = tk.StringVar(value="COM3")
            self.visa_resource_var = tk.StringVar(value="GPIB0::22::INSTR")
            self.visa_resource_combo = None
            self.baud_var = tk.StringVar(value="9600")
            self.parity_var = tk.StringVar(value="none")
            self.data_bits_var = tk.StringVar(value="8")
            self.timeout_var = tk.StringVar(value="10")
            self.verify_identity_var = tk.BooleanVar(value=True)

            self.function_var = tk.StringVar(value="DC Voltage")
            self.range_var = tk.StringVar(value="AUTO")
            self.nplc_var = tk.StringVar(value="10")
            self.ac_filter_var = tk.StringVar(value="20")
            self.interval_var = tk.StringVar(value="1.0")

            self.expected_ohm_var = tk.StringVar(value="10000")
            self.stable_range_var = tk.StringVar(value="AUTO")
            self.stable_4w_var = tk.BooleanVar(value=False)
            self.min_settle_var = tk.StringVar(value="0.5")
            self.max_wait_var = tk.StringVar(value="20")
            self.rel_stdev_var = tk.StringVar(value="0.0005")
            self.rel_slope_var = tk.StringVar(value="0.0005")

            self.log_enabled_var = tk.BooleanVar(value=False)
            self.log_path_var = tk.StringVar(value=str(Path.cwd() / "hp34401a_gui_log.csv"))
            self.raw_command_var = tk.StringVar(value="*IDN?")

            self._build_ui(ttk, tk, filedialog, messagebox)
            self.root.protocol("WM_DELETE_WINDOW", self._on_close)
            self.root.after(100, self._poll_events)
            self._update_range_choices()
            # Fill the VISA resource drop-down shortly after the window opens.
            # Failure is non-fatal because serial-only PCs may not have VISA.
            self.root.after(300, self.refresh_visa_resources)

        def _build_ui(self, ttk, tk, filedialog, messagebox) -> None:  # noqa: ANN001
            self.filedialog = filedialog
            self.messagebox = messagebox
            self.root.columnconfigure(1, weight=1)
            self.root.rowconfigure(0, weight=1)

            left = ttk.Frame(self.root, padding=10)
            left.grid(row=0, column=0, sticky="ns")
            center = ttk.Frame(self.root, padding=10)
            center.grid(row=0, column=1, sticky="nsew")
            center.columnconfigure(0, weight=1)
            center.rowconfigure(2, weight=1)

            conn = ttk.LabelFrame(left, text="Connection", padding=8)
            conn.pack(fill="x", pady=(0, 8))
            self._combo(conn, "Transport", self.transport_var, ["VISA GPIB", "Serial RS-232"], 0)
            self._entry(conn, "Serial port", self.serial_port_var, 1)
            self.visa_resource_combo = self._combo(
                conn, "VISA resource", self.visa_resource_var, [self.visa_resource_var.get()], 2
            )
            ttk.Button(conn, text="Refresh VISA list", command=self.refresh_visa_resources).grid(
                row=3, column=0, columnspan=2, sticky="ew", pady=(2, 5)
            )
            self._entry(conn, "Baud", self.baud_var, 4)
            self._combo(conn, "Parity", self.parity_var, ["none", "even", "odd"], 5)
            self._entry(conn, "Data bits", self.data_bits_var, 6)
            self._entry(conn, "Timeout s", self.timeout_var, 7)
            ttk.Checkbutton(conn, text="Verify 34401A identity", variable=self.verify_identity_var).grid(row=8, column=0, columnspan=2, sticky="w")
            ttk.Button(conn, text="Connect", command=self.connect).grid(row=9, column=0, sticky="ew", pady=3)
            ttk.Button(conn, text="Disconnect", command=self.disconnect).grid(row=9, column=1, sticky="ew", pady=3)

            status = ttk.LabelFrame(left, text="Instrument", padding=8)
            status.pack(fill="x", pady=(0, 8))
            self.identity_label = ttk.Label(status, text="Not connected", wraplength=270)
            self.identity_label.pack(fill="x")
            self.status_label = ttk.Label(status, text="State: CLOSED")
            self.status_label.pack(fill="x", pady=(4, 0))
            ttk.Button(status, text="Identify", command=self.identify).pack(fill="x", pady=2)
            ttk.Button(status, text="Self Test", command=self.self_test).pack(fill="x", pady=2)
            ttk.Button(status, text="Clear Status (*CLS)", command=self.clear_status).pack(fill="x", pady=2)
            ttk.Button(status, text="Drain Error Queue", command=self.drain_errors).pack(fill="x", pady=2)
            ttk.Button(status, text="Query Terminals", command=self.query_terminals).pack(fill="x", pady=2)

            meas = ttk.LabelFrame(left, text="Measurement Setup", padding=8)
            meas.pack(fill="x", pady=(0, 8))
            self.function_combo = self._combo(meas, "Function", self.function_var, list(RANGE_PRESETS), 0)
            self.function_combo.bind("<<ComboboxSelected>>", lambda _e: self._update_range_choices())
            self.range_combo = self._combo(meas, "Range", self.range_var, RANGE_PRESETS[self.function_var.get()], 1)
            self._combo(meas, "NPLC", self.nplc_var, ["0.02", "0.2", "1", "10", "100"], 2)
            self._combo(meas, "AC filter Hz", self.ac_filter_var, ["3", "20", "200"], 3)
            self._entry(meas, "Interval s", self.interval_var, 4)
            ttk.Button(meas, text="Single Read", command=self.single_read).grid(row=5, column=0, sticky="ew", pady=3)
            ttk.Button(meas, text="Start Continuous", command=self.start_continuous).grid(row=5, column=1, sticky="ew", pady=3)
            ttk.Button(meas, text="Stop", command=self.stop_continuous).grid(row=6, column=0, columnspan=2, sticky="ew", pady=3)
            ttk.Button(meas, text="BUS Trigger Read", command=self.bus_trigger_read).grid(row=7, column=0, columnspan=2, sticky="ew", pady=3)

            stable = ttk.LabelFrame(left, text="Stable Resistance", padding=8)
            stable.pack(fill="x")
            self._entry(stable, "Expected Ω", self.expected_ohm_var, 0)
            self._entry(stable, "Range Ω/AUTO", self.stable_range_var, 1)
            ttk.Checkbutton(stable, text="4-wire", variable=self.stable_4w_var).grid(row=2, column=0, columnspan=2, sticky="w")
            self._entry(stable, "Min settle s", self.min_settle_var, 3)
            self._entry(stable, "Max wait s", self.max_wait_var, 4)
            self._entry(stable, "Rel stdev", self.rel_stdev_var, 5)
            self._entry(stable, "Rel slope/s", self.rel_slope_var, 6)
            ttk.Button(stable, text="Read Stable Ω", command=self.read_stable).grid(row=7, column=0, columnspan=2, sticky="ew", pady=3)

            display = tk.Frame(center, bg="#101610", bd=2, relief="sunken")
            display.grid(row=0, column=0, sticky="ew")
            display.columnconfigure(0, weight=1)
            self.value_label = tk.Label(display, text="--.------", font=("Consolas", 58, "bold"), fg="#78ff78", bg="#101610", anchor="e")
            self.value_label.grid(row=0, column=0, sticky="ew", padx=15, pady=(14, 0))
            self.unit_label = tk.Label(display, text="", font=("Consolas", 26, "bold"), fg="#bfffbf", bg="#101610", anchor="w")
            self.unit_label.grid(row=0, column=1, sticky="w", padx=(0, 15), pady=(14, 0))
            self.display_sub_label = tk.Label(display, text="Ready", font=("Consolas", 13), fg="#c8ffc8", bg="#101610", anchor="w")
            self.display_sub_label.grid(row=1, column=0, columnspan=2, sticky="ew", padx=18, pady=(0, 10))

            logframe = ttk.LabelFrame(center, text="Logging", padding=8)
            logframe.grid(row=1, column=0, sticky="ew", pady=8)
            logframe.columnconfigure(1, weight=1)
            ttk.Checkbutton(logframe, text="Enable CSV", variable=self.log_enabled_var).grid(row=0, column=0, sticky="w")
            ttk.Entry(logframe, textvariable=self.log_path_var).grid(row=0, column=1, sticky="ew", padx=5)
            ttk.Button(logframe, text="Browse", command=self.choose_log).grid(row=0, column=2)

            self.plot = tk.Canvas(center, height=210, bg="white", bd=1, relief="sunken")
            self.plot.grid(row=2, column=0, sticky="nsew", pady=(0, 8))

            raw = ttk.LabelFrame(center, text="Raw SCPI / Event Log", padding=8)
            raw.grid(row=3, column=0, sticky="nsew")
            raw.columnconfigure(0, weight=1)
            ttk.Entry(raw, textvariable=self.raw_command_var).grid(row=0, column=0, sticky="ew", padx=(0, 4))
            ttk.Button(raw, text="Query", command=self.raw_query).grid(row=0, column=1, padx=2)
            ttk.Button(raw, text="Write", command=self.raw_write).grid(row=0, column=2, padx=2)
            self.log_text = tk.Text(raw, height=10, wrap="word")
            self.log_text.grid(row=1, column=0, columnspan=3, sticky="nsew", pady=(6, 0))

        def _entry(self, parent, label: str, var, row: int):  # noqa: ANN001
            ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=2)
            ent = ttk.Entry(parent, textvariable=var, width=18)
            ent.grid(row=row, column=1, sticky="ew", pady=2)
            return ent

        def _combo(self, parent, label: str, var, values: list[str], row: int):  # noqa: ANN001
            ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=2)
            cb = ttk.Combobox(parent, textvariable=var, values=values, width=22)
            cb.grid(row=row, column=1, sticky="ew", pady=2)
            return cb

        def _update_range_choices(self) -> None:
            values = RANGE_PRESETS.get(self.function_var.get(), ["AUTO"])
            self.range_combo.configure(values=values)
            self.range_var.set("AUTO")

        def _build_driver(self) -> Hp34401A:
            cfg = DriverConfig(
                default_timeout_s=float(self.timeout_var.get()),
                verify_identity_on_connect=self.verify_identity_var.get(),
                raw_traffic_log=False,
            )
            if self.transport_var.get() == "Serial RS-232":
                scfg = SerialRs232Config(
                    port=self.serial_port_var.get().strip(),
                    baudrate=int(self.baud_var.get()),
                    parity=self.parity_var.get(),
                    data_bits=int(self.data_bits_var.get()),
                )
                return Hp34401A.from_serial(scfg, cfg)
            resource = _normalize_visa_resource(self.visa_resource_var.get())
            if not resource:
                raise ValueError("VISA resource is empty. Click Refresh VISA list or enter a resource manually.")
            vcfg = VisaGpibConfig(resource=resource)
            return Hp34401A.from_visa_gpib(vcfg, cfg)

        def _worker(self, label: str, func: Callable[[], Any]) -> None:
            def run() -> None:
                if not self.state.worker_lock.acquire(blocking=False):
                    self.events.put(("log", "Another instrument operation is still running"))
                    return
                try:
                    self.events.put(("busy", label))
                    result = func()
                    self.events.put(("result", (label, result)))
                except Exception as exc:  # noqa: BLE001 - GUI must not crash on I/O errors
                    self.events.put(("error", (label, exc)))
                finally:
                    self.state.worker_lock.release()
                    self.events.put(("busy", "Ready"))
            threading.Thread(target=run, daemon=True).start()

        def connect(self) -> None:
            def do() -> str:
                if self.state.driver is not None:
                    self.state.driver.close()
                self.state.driver = self._build_driver()
                self.state.driver.connect()
                ident = self.state.driver.identity_cached or self.state.driver.identify()
                self.state.connected = True
                return f"{ident.manufacturer} {ident.model} serial={ident.serial} fw={ident.firmware}"
            self._worker("Connect", do)

        def disconnect(self) -> None:
            def do() -> str:
                self.state.continuous_stop.set()
                if self.state.driver is not None:
                    self.state.driver.close()
                self.state.connected = False
                return "Disconnected"
            self._worker("Disconnect", do)

        def _require_driver(self) -> Hp34401A:
            if self.state.driver is None or not self.state.driver.is_connected():
                raise Hp34401AError("Not connected")
            return self.state.driver

        def refresh_visa_resources(self) -> None:
            """Refresh the VISA resource combobox with resources visible to PyVISA."""
            def do() -> list[str]:
                return _list_visa_resources()

            self._worker("Refresh VISA Resources", do)

        def _apply_visa_resource_list(self, resources: list[str]) -> None:
            if self.visa_resource_combo is not None:
                self.visa_resource_combo.configure(values=resources)
            current = _normalize_visa_resource(self.visa_resource_var.get())
            if resources and (not current or current not in resources):
                self.visa_resource_var.set(resources[0])
            if resources:
                self._log("VISA resources found: " + ", ".join(resources))
            else:
                self._log("No VISA resources found. Verify NI-VISA/Keysight IO Libraries and adapter connection.")

        def _measure(self) -> MeasurementReading:
            d = self._require_driver()
            rng = _parse_range(self.range_var.get())
            func = self.function_var.get()
            if func == "DC Voltage":
                return d.measure_dc_voltage(rng, _parse_nplc(self.nplc_var.get()))
            if func == "AC Voltage":
                return d.measure_ac_voltage(rng, _parse_ac_filter(self.ac_filter_var.get()))
            if func == "DC Current":
                return d.measure_dc_current(rng, _parse_nplc(self.nplc_var.get()))
            if func == "Resistance 2W":
                return d.measure_2wire_resistance(rng, _parse_nplc(self.nplc_var.get()))
            if func == "Resistance 4W":
                return d.measure_4wire_resistance(rng, _parse_nplc(self.nplc_var.get()))
            raise ValueError(f"Unsupported GUI function: {func}")

        def single_read(self) -> None:
            self._worker("Single Read", self._measure)

        def bus_trigger_read(self) -> None:
            def do() -> MeasurementReading:
                d = self._require_driver()
                # Configure first using the normal selected function/range, then use bus trigger.
                rng = _parse_range(self.range_var.get())
                func = self.function_var.get()
                if func == "DC Voltage":
                    d.configure_dc_voltage(rng, _parse_nplc(self.nplc_var.get()))
                elif func == "Resistance 2W":
                    d.configure_2wire_resistance(rng, _parse_nplc(self.nplc_var.get()))
                elif func == "Resistance 4W":
                    d.configure_4wire_resistance(rng, _parse_nplc(self.nplc_var.get()))
                elif func == "AC Voltage":
                    d.configure_ac_voltage(rng, _parse_ac_filter(self.ac_filter_var.get()))
                elif func == "DC Current":
                    d.configure_dc_current(rng, _parse_nplc(self.nplc_var.get()))
                else:
                    raise ValueError(f"Unsupported BUS-trigger function: {func}")
                return d.read_once_bus()
            self._worker("BUS Trigger Read", do)

        def start_continuous(self) -> None:
            self.state.continuous_stop.clear()
            interval = float(self.interval_var.get())

            def loop() -> str:
                while not self.state.continuous_stop.is_set():
                    try:
                        reading = self._measure()
                        self.events.put(("reading", ("Continuous", reading)))
                    except Exception as exc:  # noqa: BLE001
                        self.events.put(("error", ("Continuous", exc)))
                    self.state.continuous_stop.wait(max(0.05, interval))
                return "Continuous stopped"
            self._worker("Continuous", loop)

        def stop_continuous(self) -> None:
            self.state.continuous_stop.set()
            self._log("Stop requested")

        def read_stable(self) -> None:
            def do():
                d = self._require_driver()
                expected = float(self.expected_ohm_var.get()) if self.expected_ohm_var.get().strip() else None
                profile = StabilityProfile(
                    expected_ohm=expected,
                    range_ohm=_parse_range(self.stable_range_var.get()),
                    nplc=_parse_nplc(self.nplc_var.get()),
                    min_settle_s=float(self.min_settle_var.get()),
                    max_wait_s=float(self.max_wait_var.get()),
                    max_relative_stdev=float(self.rel_stdev_var.get()),
                    max_slope_relative_per_s=float(self.rel_slope_var.get()),
                    four_wire=self.stable_4w_var.get(),
                )
                return d.read_stable_resistance(profile)
            self._worker("Stable Resistance", do)

        def identify(self) -> None:
            self._worker("Identify", lambda: self._require_driver().identify())

        def self_test(self) -> None:
            self._worker("Self Test", lambda: self._require_driver().self_test())

        def clear_status(self) -> None:
            self._worker("Clear Status", lambda: self._require_driver().clear_status() or "*CLS sent")

        def drain_errors(self) -> None:
            self._worker("Drain Error Queue", lambda: self._require_driver().drain_error_queue())

        def query_terminals(self) -> None:
            self._worker("Query Terminals", lambda: self._require_driver().query_terminal())

        def raw_query(self) -> None:
            cmd = self.raw_command_var.get().strip()
            self._worker(f"Query {cmd}", lambda: self._require_driver().query(cmd))

        def raw_write(self) -> None:
            cmd = self.raw_command_var.get().strip()
            self._worker(f"Write {cmd}", lambda: self._require_driver().write(cmd) or "OK")

        def choose_log(self) -> None:
            name = self.filedialog.asksaveasfilename(
                defaultextension=".csv", filetypes=[("CSV", "*.csv"), ("All files", "*.*")]
            )
            if name:
                self.log_path_var.set(name)

        def _poll_events(self) -> None:
            try:
                while True:
                    kind, payload = self.events.get_nowait()
                    if kind == "busy":
                        self.status_label.configure(text=f"State: {payload}")
                        self.display_sub_label.configure(text=str(payload))
                    elif kind == "log":
                        self._log(str(payload))
                    elif kind == "error":
                        label, exc = payload
                        self._log(f"ERROR during {label}: {exc}")
                        self.display_sub_label.configure(text=f"ERROR: {exc}")
                    elif kind == "result":
                        label, result = payload
                        self._handle_result(label, result)
                    elif kind == "reading":
                        label, reading = payload
                        self._handle_reading(label, reading)
            except queue.Empty:
                pass
            self.root.after(100, self._poll_events)

        def _handle_result(self, label: str, result: Any) -> None:
            if label == "Refresh VISA Resources" and isinstance(result, list):
                self._apply_visa_resource_list([str(r) for r in result])
                return
            if isinstance(result, MeasurementReading):
                self._handle_reading(label, result)
                return
            if hasattr(result, "stable") and hasattr(result, "value"):
                text = f"stable={result.stable} value={result.value} {result.unit} reason={result.reason}"
                self._log(f"{label}: {text}")
                if getattr(result, "reading", None) is not None:
                    self._handle_reading(label, result.reading)
                else:
                    self.value_label.configure(text="NO STABLE")
                    self.unit_label.configure(text="")
                    self.display_sub_label.configure(text=text)
                return
            text = str(result)
            self._log(f"{label}: {text}")
            if label == "Connect":
                self.identity_label.configure(text=text)

        def _handle_reading(self, source: str, reading: MeasurementReading) -> None:
            self.state.readings.append(reading)
            self.state.readings = self.state.readings[-300:]
            if reading.is_overload:
                self.value_label.configure(text="OVERLOAD")
                self.unit_label.configure(text=reading.unit)
            elif reading.value is None:
                self.value_label.configure(text="INVALID")
                self.unit_label.configure(text=reading.unit)
            else:
                self.value_label.configure(text=f"{reading.value:.8g}")
                self.unit_label.configure(text=reading.unit)
            self.display_sub_label.configure(
                text=f"{reading.function.name}  retried={reading.was_retried}  raw={reading.raw}"
            )
            self._log(f"{source}: {reading.value} {reading.unit} raw={reading.raw}")
            if self.log_enabled_var.get():
                try:
                    _append_csv(Path(self.log_path_var.get()), reading, source)
                except OSError as exc:
                    self._log(f"LOG ERROR: {exc}")
            self._draw_plot()

        def _draw_plot(self) -> None:
            self.plot.delete("all")
            vals = [r.value for r in self.state.readings if r.value is not None and not r.is_overload]
            w = max(self.plot.winfo_width(), 50)
            h = max(self.plot.winfo_height(), 50)
            self.plot.create_rectangle(40, 15, w - 10, h - 25, outline="#cccccc")
            if len(vals) < 2:
                self.plot.create_text(w // 2, h // 2, text="Trend plot")
                return
            vals = vals[-200:]
            ymin, ymax = min(vals), max(vals)
            if ymin == ymax:
                ymin -= 1
                ymax += 1
            points = []
            for i, v in enumerate(vals):
                x = 40 + i * (w - 55) / max(1, len(vals) - 1)
                y = 15 + (ymax - v) * (h - 40) / (ymax - ymin)
                points.extend([x, y])
            self.plot.create_line(*points, width=2)
            self.plot.create_text(45, 10, anchor="w", text=f"max {ymax:.5g}")
            self.plot.create_text(45, h - 12, anchor="w", text=f"min {ymin:.5g}")

        def _log(self, text: str) -> None:
            stamp = _dt.datetime.now().strftime("%H:%M:%S")
            self.log_text.insert("end", f"[{stamp}] {text}\n")
            self.log_text.see("end")

        def _on_close(self) -> None:
            self.state.continuous_stop.set()
            try:
                if self.state.driver is not None:
                    self.state.driver.close()
            finally:
                self.root.destroy()

    try:
        root = tk.Tk()
    except Exception as exc:  # pragma: no cover - display-server dependent
        print(f"Could not start GUI. Is a desktop/display available? {exc}")
        return 2
    # Native ttk theme if available; default otherwise.
    try:
        style = ttk.Style(root)
        if "clam" in style.theme_names():
            style.theme_use("clam")
    except Exception:
        pass
    DmmGuiApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
