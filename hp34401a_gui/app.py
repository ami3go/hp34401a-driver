"""RFDS-safe launcher for the HP 34401A Tkinter GUI.

The complete reviewed GUI implementation is preserved in ``legacy_app``. This
launcher installs a narrow operator authorization gate around the two raw-SCPI
service buttons. Every raw Query/Write requires a fresh explicit confirmation;
ordinary measurement, identity, health, logging, and connection controls are
unchanged. Calibration commands remain independently guarded by the core.
"""

from __future__ import annotations

import functools
import sys
from pathlib import Path
from typing import Any, Callable

if __package__ in (None, ""):
    _project_root = Path(__file__).resolve().parents[1]
    if str(_project_root) not in sys.path:
        sys.path.insert(0, str(_project_root))
    from hp34401a_gui import legacy_app
else:
    from . import legacy_app

_RAW_SERVICE_METHODS = {"raw_query", "raw_write"}


def is_raw_service_command(command: object) -> bool:
    """Return True only for the legacy GUI's explicit raw service callbacks."""
    return getattr(command, "__name__", "") in _RAW_SERVICE_METHODS


def guarded_raw_service_call(
    command: Callable[[], Any],
    confirm: Callable[[], bool],
) -> Any:
    """Execute one raw service action only after explicit operator approval."""
    if not confirm():
        return None
    return command()


def main() -> int:
    try:
        from tkinter import messagebox, ttk
    except Exception as exc:  # pragma: no cover - environment dependent
        print(f"Tkinter GUI is not available in this Python environment: {exc}")
        return 2

    original_button = ttk.Button

    def safe_button(master=None, **kwargs):  # noqa: ANN001, ANN003
        command = kwargs.get("command")
        if is_raw_service_command(command):
            raw_command = command

            @functools.wraps(raw_command)
            def authorized() -> Any:
                return guarded_raw_service_call(
                    raw_command,
                    lambda: bool(
                        messagebox.askyesno(
                            "Raw SCPI service authorization",
                            "Raw SCPI can change instrument state and bypass high-level "
                            "measurement sequencing. Authorize this single raw operation?",
                            icon="warning",
                        )
                    ),
                )

            kwargs["command"] = authorized
            label = str(kwargs.get("text") or "Raw")
            kwargs["text"] = f"{label} (service)"
        return original_button(master, **kwargs)

    # legacy_app.main imports the shared tkinter.ttk module at call time, so
    # this narrowly scoped replacement affects its Button constructor without
    # changing the preserved GUI source. Restore it even when GUI startup fails.
    ttk.Button = safe_button  # type: ignore[assignment]
    try:
        return int(legacy_app.main())
    finally:
        ttk.Button = original_button  # type: ignore[assignment]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = ["guarded_raw_service_call", "is_raw_service_command", "main"]
