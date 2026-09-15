"""RFDS-019 call and protocol conformance harness.

This test-only Robot library invokes the public DMM library through Robot
Framework's BuiltIn API and observes the deterministic FakeTransport at the
same SCPI boundary used by the production driver.
"""

from __future__ import annotations

import csv
import json
import os
import platform
import re
import sys
import tempfile
import types
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import robot
import yaml
from robot.api.deco import keyword, library
from robot.libdocpkg import LibraryDocumentation
from robot.libraries.BuiltIn import BuiltIn

from hp34401a_dmm import DriverConfig, FakeTransport, Hp34401A
from hp34401a_dmm.enums import TransportType


@library(scope="SUITE", auto_keywords=False)
class ConformanceHarness:
    """Execute and report the RFDS-019 software conformance profile."""

    ROBOT_LIBRARY_SCOPE = "SUITE"
    ROBOT_AUTO_KEYWORDS = False

    def __init__(self) -> None:
        self._root = Path(__file__).resolve().parents[3]
        self._data = self._root / "tests" / "conformance" / "data"
        self._built_in = BuiltIn()
        self._results: list[dict[str, Any]] = []
        self._outbound_lines: list[str] = []
        self._inbound_lines: list[str] = []

    @keyword("Run Full Driver Call Protocol Conformance")
    def run_full_driver_call_protocol_conformance(self, output_dir: str) -> None:
        """Run every vector, generate RFDS-019 evidence, and fail on any defect."""
        self._results.clear()
        self._outbound_lines.clear()
        self._inbound_lines.clear()
        destination = Path(output_dir).resolve()
        destination.mkdir(parents=True, exist_ok=True)
        vectors_doc = self._load_yaml(self._data / "protocol_vectors.yaml")
        vectors = list(vectors_doc.get("vectors", []))
        error_vectors = list(vectors_doc.get("protocol_error_vectors", []))
        inventory_doc = self._load_yaml(self._data / "keyword_inventory.yaml")
        exclusions_doc = self._load_yaml(self._data / "exclusions.yaml")

        inventory_errors = self._validate_inventory(inventory_doc, vectors)
        for error in inventory_errors:
            self._results.append(
                {
                    "vector_id": "INVENTORY",
                    "keyword": "<inventory>",
                    "result": "FAIL",
                    "reason": error,
                }
            )

        for vector in vectors:
            self._run_vector(vector)
        for vector in error_vectors:
            self._run_error_vector(vector)

        self._write_evidence(destination, inventory_doc, exclusions_doc)
        failures = [item for item in self._results if item.get("result") == "FAIL"]
        if failures:
            details = "; ".join(
                f"{item.get('vector_id')} {item.get('keyword')}: {item.get('reason')}"
                for item in failures[:10]
            )
            raise AssertionError(
                f"RFDS-019 conformance failed ({len(failures)} failures): {details}"
            )

    def _load_yaml(self, path: Path) -> dict[str, Any]:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise AssertionError(  # noqa: TRY004 - malformed file content, not a Python type error
                f"Expected YAML mapping in {path}"
            )
        return loaded

    def _actual_keywords(self) -> list[dict[str, Any]]:
        doc = LibraryDocumentation("rf_hp34401a.Hp34401ALibrary")
        output: list[dict[str, Any]] = []
        for item in doc.keywords:
            output.append(
                {
                    "keyword": item.name,
                    "arguments": [str(arg) for arg in item.args],
                }
            )
        return sorted(output, key=lambda item: item["keyword"])

    def _validate_inventory(
        self, inventory_doc: dict[str, Any], vectors: list[dict[str, Any]]
    ) -> list[str]:
        errors: list[str] = []
        actual = self._actual_keywords()
        actual_names = {item["keyword"] for item in actual}
        inventory = list(inventory_doc.get("keywords", []))
        inventory_names = {str(item.get("keyword")) for item in inventory}
        vector_names = {str(item.get("keyword")) for item in vectors}
        if actual_names != inventory_names:
            errors.append(
                "keyword inventory mismatch: "
                f"missing={sorted(actual_names - inventory_names)}, "
                f"extra={sorted(inventory_names - actual_names)}"
            )
        if actual_names != vector_names:
            errors.append(
                "protocol vector coverage mismatch: "
                f"missing={sorted(actual_names - vector_names)}, "
                f"extra={sorted(vector_names - actual_names)}"
            )
        if len(inventory) != len(inventory_names):
            errors.append("keyword_inventory.yaml contains duplicate keyword entries")
        return errors

    @property
    def _library(self) -> Any:
        for name in (
            "rf_hp34401a.Hp34401ALibrary",
            "Hp34401ALibrary",
            "rf_hp34401a",
        ):
            try:
                return self._built_in.get_library_instance(name)
            except RuntimeError:
                continue
        raise RuntimeError("Could not resolve the Hp34401ALibrary Robot instance")

    @contextmanager
    def _patched_environment(self, vector: dict[str, Any]) -> Iterator[None]:
        factory = vector.get("factory")
        # `Hp34401A` (hp34401a_dmm.driver.Hp34401A) inherits from_visa_gpib/
        # from_serial from legacy_driver.Hp34401A rather than redefining them,
        # so they are not necessarily in Hp34401A.__dict__ itself. Use a
        # sentinel so the finally block can tell "inherited" apart from
        # "overridden directly on this class" and restore either correctly.
        _unset = object()
        original_visa = Hp34401A.__dict__.get("from_visa_gpib", _unset)
        original_serial = Hp34401A.__dict__.get("from_serial", _unset)
        original_pyvisa = sys.modules.get("pyvisa")
        original_profile_dir = os.environ.get("RF_HP34401A_PROFILE_DIR")
        profile_temp = tempfile.TemporaryDirectory() if vector.get("profile_temp") else None
        if profile_temp is not None:
            os.environ["RF_HP34401A_PROFILE_DIR"] = profile_temp.name

        def responses() -> dict[str, str]:
            return {
                "READ?": "12.0",
                "FETCh?": "12.0",
                "ROUTe:TERMinals?": "FRONT",
                "*TST?": "0",
                "SYSTem:VERSion?": "1991.0",
            }

        if factory in {"visa", "connect_visa"}:

            def visa_factory(
                cls: type[Hp34401A], config: Any, driver_config: DriverConfig | None = None
            ) -> Hp34401A:
                transport = FakeTransport(responses=responses())
                transport.config = config  # type: ignore[attr-defined]
                return cls(transport, driver_config or DriverConfig())

            Hp34401A.from_visa_gpib = classmethod(visa_factory)

        if factory == "serial":

            class SerialFakeTransport(FakeTransport):
                _transport_type = TransportType.SERIAL_RS232

            def serial_factory(
                cls: type[Hp34401A], config: Any, driver_config: DriverConfig | None = None
            ) -> Hp34401A:
                transport = SerialFakeTransport(responses=responses())
                transport.config = config  # type: ignore[attr-defined]
                return cls(transport, driver_config or DriverConfig())

            Hp34401A.from_serial = classmethod(serial_factory)

        if vector.get("pyvisa_stub"):

            class ResourceManager:
                def __init__(self, _library: str = "") -> None:
                    self.closed = False

                def list_resources(self) -> tuple[str, ...]:
                    return ("GPIB0::22::INSTR", "USB0::SIM::INSTR")

                def close(self) -> None:
                    self.closed = True

            sys.modules["pyvisa"] = types.SimpleNamespace(ResourceManager=ResourceManager)

        try:
            yield
        finally:
            if original_visa is _unset:
                if "from_visa_gpib" in Hp34401A.__dict__:
                    delattr(Hp34401A, "from_visa_gpib")
            else:
                Hp34401A.from_visa_gpib = original_visa
            if original_serial is _unset:
                if "from_serial" in Hp34401A.__dict__:
                    delattr(Hp34401A, "from_serial")
            else:
                Hp34401A.from_serial = original_serial
            if vector.get("pyvisa_stub"):
                if original_pyvisa is None:
                    sys.modules.pop("pyvisa", None)
                else:
                    sys.modules["pyvisa"] = original_pyvisa
            if profile_temp is not None:
                profile_temp.cleanup()
                if original_profile_dir is None:
                    os.environ.pop("RF_HP34401A_PROFILE_DIR", None)
                else:
                    os.environ["RF_HP34401A_PROFILE_DIR"] = original_profile_dir

    def _run_setup(self, vector: dict[str, Any]) -> None:
        self._safe_close_all()
        for call in vector.get("setup_calls", []):
            self._built_in.run_keyword(str(call["keyword"]), *list(call.get("arguments", [])))
        mutation = vector.get("transport_mutation", {})
        if mutation:
            alias = str(mutation.get("alias", "dut"))
            transport = self._library._sessions.get(alias).driver._t
            if "responses" in mutation:
                transport.responses.update(dict(mutation["responses"]))
            if "error_queue" in mutation:
                transport.error_queue.extend(list(mutation["error_queue"]))
            if "timeout_on" in mutation:
                transport.timeout_on.update(set(mutation["timeout_on"]))

    def _safe_close_all(self) -> None:
        try:
            self._built_in.run_keyword("Close All DMMs")
        except Exception:  # noqa: BLE001 - falls back to direct close below
            try:
                self._library.close()
            except Exception:  # noqa: BLE001, S110 - best-effort teardown between vectors
                pass

    def _current_transports(self) -> list[Any]:
        sessions = getattr(self._library, "_sessions", None)
        if sessions is None:
            return []
        result: list[Any] = []
        for alias in sessions.aliases():
            result.append(sessions.get(alias).driver._t)
        return result

    @staticmethod
    def _clear_transport_trace(transports: list[Any]) -> dict[int, int]:
        clears: dict[int, int] = {}
        for transport in transports:
            transport.history.clear()
            transport.write_history.clear()
            transport.query_history.clear()
            if hasattr(transport, "response_history"):
                transport.response_history.clear()
            clears[id(transport)] = int(getattr(transport, "clear_count", 0))
        return clears

    def _run_vector(self, vector: dict[str, Any]) -> None:
        vector_id = str(vector["id"])
        keyword_name = str(vector["keyword"])
        result_row: dict[str, Any] = {
            "vector_id": vector_id,
            "keyword": keyword_name,
            "canonical_keyword": vector.get("canonical_keyword", keyword_name),
            "device_facing": bool(vector.get("device_facing", False)),
            "result": "FAIL",
        }
        try:
            with self._patched_environment(vector):
                self._run_setup(vector)
                before = self._current_transports()
                baseline_clears = self._clear_transport_trace(before)
                arguments = self._expand_arguments(list(vector.get("arguments", [])))
                start = datetime.now(timezone.utc)
                value = self._built_in.run_keyword(keyword_name, *arguments)
                end = datetime.now(timezone.utc)
                after = self._current_transports()
                observed = list(dict.fromkeys(before + after))
                outbound = [cmd for transport in observed for cmd in transport.history]
                inbound = [
                    (cmd, response)
                    for transport in observed
                    for cmd, response in getattr(transport, "response_history", [])
                ]
                clear_delta = sum(
                    int(getattr(transport, "clear_count", 0))
                    - baseline_clears.get(id(transport), 0)
                    for transport in observed
                )
                self._verify_outbound(vector, outbound, inbound, clear_delta)
                self._verify_return(vector.get("expected_return", {}), value)
                result_row.update(
                    {
                        "result": "PASS",
                        "duration_s": (end - start).total_seconds(),
                        "outbound": outbound,
                        "inbound": [
                            {"operation": command, "raw_response": response}
                            for command, response in inbound
                        ],
                        "return_type": self._robot_type(value),
                        "clear_count_delta": clear_delta,
                    }
                )
                self._record_trace(vector_id, keyword_name, outbound, inbound)
        except Exception as exc:  # noqa: BLE001 - any vector failure is recorded as a FAIL row
            result_row["reason"] = f"{type(exc).__name__}: {exc}"
        finally:
            self._results.append(result_row)
            self._safe_close_all()

    def _run_error_vector(self, vector: dict[str, Any]) -> None:
        vector_id = str(vector["id"])
        keyword_name = str(vector["keyword"])
        row: dict[str, Any] = {
            "vector_id": vector_id,
            "keyword": keyword_name,
            "protocol_error_vector": True,
            "result": "FAIL",
        }
        try:
            with self._patched_environment(vector):
                self._run_setup(vector)
                transport = self._library._sessions.get("dut").driver._t
                self._clear_transport_trace([transport])
                expected_pattern = str(vector["expected_error_pattern"])
                error_text = self._built_in.run_keyword_and_expect_error(
                    expected_pattern,
                    keyword_name,
                    *self._expand_arguments(list(vector.get("arguments", []))),
                )
                outbound = list(transport.history)
                inbound = list(getattr(transport, "response_history", []))
                self._record_trace(vector_id, keyword_name, outbound, inbound)
                recovery = vector.get("recovery")
                if recovery:
                    for command in vector.get("remove_timeout_on", []):
                        transport.timeout_on.discard(command)
                    transport.responses.update(dict(vector.get("recovery_responses", {})))
                    recovery_value = self._built_in.run_keyword(
                        str(recovery["keyword"]), *list(recovery.get("arguments", []))
                    )
                    self._verify_return(recovery.get("expected_return", {}), recovery_value)
                row.update(
                    {
                        "result": "PASS",
                        "expected_error": expected_pattern,
                        "actual_error": str(error_text),
                        "outbound": outbound,
                        "inbound": [
                            {"operation": command, "raw_response": response}
                            for command, response in inbound
                        ],
                        "recovery_tested": bool(recovery),
                    }
                )
        except Exception as exc:  # noqa: BLE001 - any vector failure is recorded as a FAIL row
            row["reason"] = f"{type(exc).__name__}: {exc}"
        finally:
            self._results.append(row)
            self._safe_close_all()

    @staticmethod
    def _expand_arguments(arguments: list[Any]) -> list[Any]:
        output: list[Any] = []
        for value in arguments:
            if value == "$STABLE_RESULT":
                output.append({"stable": True, "value": 1000.0})
            else:
                output.append(value)
        return output

    @staticmethod
    def _verify_outbound(
        vector: dict[str, Any],
        outbound: list[str],
        inbound: list[tuple[str, str]],
        clear_delta: int,
    ) -> None:
        expected = vector.get("expected_outbound", {})
        operations = list(expected.get("contains_in_order", []))
        position = -1
        for operation in operations:
            try:
                position = outbound.index(str(operation), position + 1)
            except ValueError as exc:
                raise AssertionError(
                    f"Missing or out-of-order protocol operation {operation!r}; actual={outbound}"
                ) from exc
        for operation in expected.get("contains", []):
            if str(operation) not in outbound:
                raise AssertionError(f"Missing protocol operation {operation!r}; actual={outbound}")
        for pattern in expected.get("contains_regex", []):
            if not any(re.fullmatch(str(pattern), command) for command in outbound):
                raise AssertionError(f"No outbound command matched {pattern!r}; actual={outbound}")
        for forbidden in expected.get("forbidden", []):
            if str(forbidden) in outbound:
                raise AssertionError(f"Forbidden protocol operation {forbidden!r} was transmitted")
        if expected.get("none") and outbound:
            raise AssertionError(f"Expected no outbound protocol data; actual={outbound}")
        if "clear_count_min" in expected and clear_delta < int(expected["clear_count_min"]):
            raise AssertionError(
                f"Expected at least {expected['clear_count_min']} transport clear(s), got {clear_delta}"
            )
        inbound_expected = vector.get("expected_inbound", {})
        if inbound_expected.get("response_required") and not inbound:
            raise AssertionError("Expected inbound protocol response but none was captured")
        if inbound_expected.get("no_response") and inbound:
            raise AssertionError(f"Expected command-only operation; inbound={inbound}")
        raw_values = [response for _, response in inbound]
        for raw in inbound_expected.get("raw_contains", []):
            if str(raw) not in raw_values:
                raise AssertionError(f"Expected raw response {raw!r}; actual={raw_values}")

    @classmethod
    def _verify_return(cls, expected: dict[str, Any], value: Any) -> None:
        expected_type = expected.get("type")
        if expected_type and cls._robot_type(value) != expected_type:
            raise AssertionError(
                f"Expected return type {expected_type}, got {cls._robot_type(value)} ({value!r})"
            )
        if "exact" in expected and value != expected["exact"]:
            raise AssertionError(f"Expected return {expected['exact']!r}, got {value!r}")
        if "contains" in expected and str(expected["contains"]) not in str(value):
            raise AssertionError(f"Return does not contain {expected['contains']!r}: {value!r}")
        if isinstance(value, dict):
            missing = set(expected.get("required_keys", [])) - set(value)
            if missing:
                raise AssertionError(f"Return dictionary missing keys: {sorted(missing)}")
        if (
            isinstance(value, list)
            and expected.get("minimum_length") is not None
            and len(value) < int(expected["minimum_length"])
        ):
            raise AssertionError(
                f"Expected list length >= {expected['minimum_length']}, got {len(value)}"
            )

    @staticmethod
    def _robot_type(value: Any) -> str:
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, int):
            return "integer"
        if isinstance(value, float):
            return "float"
        if isinstance(value, str):
            return "string"
        if isinstance(value, list):
            return "list"
        if isinstance(value, dict):
            return "dictionary"
        return type(value).__name__

    def _record_trace(
        self,
        vector_id: str,
        keyword_name: str,
        outbound: list[str],
        inbound: list[tuple[str, str]],
    ) -> None:
        for index, operation in enumerate(outbound, 1):
            self._outbound_lines.append(f"{vector_id}\t{keyword_name}\t{index}\t{operation}")
        for index, (operation, response) in enumerate(inbound, 1):
            self._inbound_lines.append(
                f"{vector_id}\t{keyword_name}\t{index}\t{operation}\t{response}"
            )

    def _write_evidence(
        self,
        destination: Path,
        inventory_doc: dict[str, Any],
        exclusions_doc: dict[str, Any],
    ) -> None:
        actual = self._actual_keywords()
        inventory_rows = []
        inventory_by_name = {
            str(item["keyword"]): item for item in inventory_doc.get("keywords", [])
        }
        result_by_keyword = {
            str(item["keyword"]): item
            for item in self._results
            if not item.get("protocol_error_vector") and item.get("keyword") != "<inventory>"
        }
        for live in actual:
            item = inventory_by_name.get(live["keyword"], {})
            result = result_by_keyword.get(live["keyword"], {})
            inventory_rows.append(
                {
                    **live,
                    "canonical_keyword": item.get("canonical_keyword", live["keyword"]),
                    "aliases": item.get("aliases", []),
                    "driver_method": item.get("driver_method"),
                    "return_type": item.get("return_type"),
                    "device_facing": item.get("device_facing"),
                    "protocol_vector": item.get("protocol_vector"),
                    "execution_status": result.get("result", "NOT RUN"),
                }
            )

        (destination / "keyword_inventory.json").write_text(
            json.dumps(inventory_rows, indent=2, sort_keys=True), encoding="utf-8"
        )
        (destination / "protocol_vector_results.json").write_text(
            json.dumps(self._results, indent=2, sort_keys=True, default=str), encoding="utf-8"
        )
        (destination / "outbound_trace.log").write_text(
            "\n".join(self._outbound_lines) + "\n", encoding="utf-8"
        )
        (destination / "inbound_trace.log").write_text(
            "\n".join(self._inbound_lines) + "\n", encoding="utf-8"
        )
        environment = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "driver_package": "rf_hp34401a",
            "driver_version": "26.07",
            "core_driver_version": "1.2.8",
            "python_version": platform.python_version(),
            "robot_framework_version": robot.__version__,
            "operating_system": platform.platform(),
            "profile": "approved_fake_transport",
            "transport_observation": "hp34401a_dmm.FakeTransport SCPI boundary",
        }
        (destination / "environment.json").write_text(
            json.dumps(environment, indent=2, sort_keys=True), encoding="utf-8"
        )
        (destination / "device_identity.json").write_text(
            json.dumps(
                {
                    "manufacturer": "HEWLETT-PACKARD",
                    "model": "34401A",
                    "serial": "SIM0001",
                    "firmware": "11-05-01",
                    "simulator": True,
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        (destination / "exclusions.json").write_text(
            json.dumps(exclusions_doc, indent=2, sort_keys=True), encoding="utf-8"
        )

        fieldnames = [
            "keyword_name",
            "canonical_keyword",
            "driver_method",
            "device_facing",
            "transport_type",
            "protocol_vector",
            "callability_tested",
            "outbound_verified",
            "raw_response_verified",
            "parsed_result_verified",
            "protocol_error_tested",
            "recovery_tested",
            "result",
            "evidence",
            "reason",
        ]
        with (destination / "keyword_coverage.csv").open(
            "w", encoding="utf-8", newline=""
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for item in inventory_rows:
                result = result_by_keyword.get(item["keyword"], {})
                device_facing = bool(item.get("device_facing"))
                writer.writerow(
                    {
                        "keyword_name": item["keyword"],
                        "canonical_keyword": item["canonical_keyword"],
                        "driver_method": item.get("driver_method", ""),
                        "device_facing": "Yes" if device_facing else "No",
                        "transport_type": "SCPI/FAKE" if device_facing else "N/A",
                        "protocol_vector": item.get("protocol_vector", ""),
                        "callability_tested": "Yes" if result else "No",
                        "outbound_verified": (
                            "PASS"
                            if device_facing and result.get("result") == "PASS"
                            else "N/A" if not device_facing else "FAIL"
                        ),
                        "raw_response_verified": "PASS" if result.get("inbound") else "N/A",
                        "parsed_result_verified": (
                            "PASS" if result.get("result") == "PASS" else "FAIL"
                        ),
                        "protocol_error_tested": (
                            "PASS" if self._error_tested(item["keyword"]) else "N/A"
                        ),
                        "recovery_tested": (
                            "PASS" if self._recovery_tested(item["keyword"]) else "N/A"
                        ),
                        "result": result.get("result", "NOT RUN"),
                        "evidence": f"protocol_vector_results.json#{item.get('protocol_vector', '')}",
                        "reason": result.get("reason", ""),
                    }
                )

        total = len(actual)
        passed = sum(1 for item in inventory_rows if item["execution_status"] == "PASS")
        device_total = sum(1 for item in inventory_rows if item.get("device_facing"))
        device_passed = sum(
            1
            for item in inventory_rows
            if item.get("device_facing") and item["execution_status"] == "PASS"
        )
        errors = [item for item in self._results if item.get("result") == "FAIL"]
        summary = f"""# RFDS-019 call and protocol conformance summary\n\n- Driver: `rf_hp34401a` 26.06\n- Profile: approved deterministic FakeTransport at the SCPI boundary\n- Exported keywords inventoried: **{total}/{total}**\n- Supported public keywords called through Robot Framework: **{passed}/{total}**\n- Device-facing keyword vectors passed: **{device_passed}/{device_total}**\n- Protocol error vectors passed: **{sum(1 for item in self._results if item.get('protocol_error_vector') and item.get('result') == 'PASS')}/{sum(1 for item in self._results if item.get('protocol_error_vector'))}**\n- Failures: **{len(errors)}**\n- Real-device representative confirmation: **SKIP — no physical HP34401A was attached; see exclusions.json**\n\n## Acceptance\n\nSoftware/simulator conformance is {'PASS' if not errors and passed == total else 'FAIL'}. Physical VISA/GPIB and RS-232 confirmation remains a separate HIL gate and is not claimed by this report.\n"""
        (destination / "conformance_summary.md").write_text(summary, encoding="utf-8")

    def _error_tested(self, keyword_name: str) -> bool:
        return any(
            item.get("protocol_error_vector")
            and item.get("keyword") == keyword_name
            and item.get("result") == "PASS"
            for item in self._results
        )

    def _recovery_tested(self, keyword_name: str) -> bool:
        return any(
            item.get("protocol_error_vector")
            and item.get("keyword") == keyword_name
            and item.get("recovery_tested")
            and item.get("result") == "PASS"
            for item in self._results
        )
