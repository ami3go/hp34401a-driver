#!/usr/bin/env python3
"""Generate the reviewed RFDS-019 keyword inventory and protocol vectors."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / "rf_hp34401a" / "library.py"
DATA = ROOT / "tests" / "conformance" / "data"


def source_surface() -> list[dict[str, Any]]:
    module = ast.parse(LIBRARY.read_text(encoding="utf-8"))
    output: list[dict[str, Any]] = []
    for node in module.body:
        if not isinstance(node, ast.ClassDef) or node.name != "Hp34401ALibrary":
            continue
        for method in node.body:
            if not isinstance(method, ast.FunctionDef):
                continue
            robot_name = None
            for decorator in method.decorator_list:
                if (
                    isinstance(decorator, ast.Call)
                    and isinstance(decorator.func, ast.Name)
                    and decorator.func.id == "keyword"
                    and decorator.args
                ):
                    robot_name = ast.literal_eval(decorator.args[0])
            if robot_name is None:
                continue
            arguments = [arg.arg for arg in method.args.args[1:]]
            defaults = [None] * (len(arguments) - len(method.args.defaults)) + [
                ast.unparse(value) for value in method.args.defaults
            ]
            output.append(
                {
                    "keyword": robot_name,
                    "driver_method": method.name,
                    "arguments": [
                        {"name": name, "required": default is None, "default": default}
                        for name, default in zip(arguments, defaults)
                    ],
                }
            )
    return sorted(output, key=lambda item: item["keyword"])


RETURN_TYPES = {
    "Export Diagnostic Bundle": "string",
    "Connect DMM": "string",
    "Open DMM Via VISA": "string",
    "Open DMM Via Serial": "string",
    "Open Simulated DMM": "string",
    "List VISA Resources": "list",
    "Select DMM": "string",
    "Get Active DMM Alias": "string",
    "Get Open DMM Aliases": "list",
    "Identify DMM": "dictionary",
    "Run DMM Self Test": "dictionary",
    "Get DMM Health": "dictionary",
    "Recover DMM": "dictionary",
    "Read DMM Error": "dictionary",
    "Get DMM Error Queue": "list",
    "Get DMM Input Terminal": "string",
    "Get DMM State": "string",
    "Get DMM Driver Version": "string",
    "Get Robot DMM Library Version": "string",
    "Get Driver Capabilities": "list",
    "Get Driver Metadata": "dictionary",
    "Read DMM": "float",
    "Measure DC Voltage": "float",
    "Measure AC Voltage": "float",
    "Measure DC Current": "float",
    "Measure AC Current": "float",
    "Measure 2 Wire Resistance": "float",
    "Measure 4 Wire Resistance": "float",
    "Measure Frequency": "float",
    "Measure Period": "float",
    "Measure Continuity": "float",
    "Measure Diode": "float",
    "Try Read Stable Resistance": "dictionary",
    "Read Stable Resistance": "float",
    "Get Last DMM Reading": "dictionary",
    "Get Last DMM Reading Value": "float",
    "Fetch DMM Readings": "list",
    "Read DMM Once With Bus Trigger": "float",
    "Query DMM Command": "string",
}

NON_DEVICE = {
    "Export Diagnostic Bundle",
    "List VISA Resources",
    "Select DMM",
    "Get Active DMM Alias",
    "Get Open DMM Aliases",
    "DMM Should Be Connected",
    "Get DMM State",
    "Get DMM Driver Version",
    "Get Robot DMM Library Version",
    "Get Driver Capabilities",
    "Get Driver Metadata",
    "Get Last DMM Reading",
    "Get Last DMM Reading Value",
    "DMM Reading Should Be Valid",
    "DMM Reading Should Not Be Overload",
    "DMM Reading Should Be Between",
    "DMM Reading Should Be Close To",
    "DMM Reading Should Be Greater Than",
    "DMM Reading Should Be Less Than",
    "Stable Resistance Should Be Between",
}

ALIAS_OF = {
    "Disconnect DMM": "Close DMM",
}


# RFDS-002 v1.1 and RFDS-013/014 additions in release 26.06.
RETURN_TYPES.update({
    "Connect": "dictionary",
    "Disconnect": "null",
    "Is Connected": "boolean",
    "Get Connection State": "dictionary",
    "Check Communication": "boolean",
    "Get Identity": "string",
    "Get Driver Information": "dictionary",
    "Get Driver Capabilities": "list",
    "Set Communication Timeout": "float",
    "Get Communication Timeout": "float",
    "List Connections": "list",
    "Select Connection": "dictionary",
    "Disconnect All": "null",
    "Get Active Connection": "string",
    "Get Device Error": "dictionary",
    "Get All Device Errors": "list",
    "Clear Device Errors": "null",
    "Device Error Queue Should Be Empty": "null",
    "Reset Device": "dictionary",
    "Get Driver Capability Model": "dictionary",
    "Get Driver Capability": "dictionary",
    "Find Driver Capabilities": "list",
    "Get Driver Features": "dictionary",
    "Refresh Driver Capabilities": "dictionary",
    "Validate Driver Capabilities": "dictionary",
    "Get Driver Configuration Schema": "dictionary",
    "Get Driver Default Configuration": "dictionary",
    "Get Driver Configuration": "dictionary",
    "Validate Driver Configuration": "dictionary",
    "Import Driver Configuration": "dictionary",
    "Export Driver Configuration": "string",
    "Save Driver Configuration": "string",
    "Load Driver Configuration": "dictionary",
    "List Driver Configuration Profiles": "list",
    "Delete Driver Configuration Profile": "null",
    "Reset Driver Configuration": "dictionary",
    "Set Raw I/O Enabled": "boolean",
    "Write Raw Command": "null",
    "Query Raw Command": "string",
    "Read Raw Response": "string",
})

NON_DEVICE.update({
    "Is Connected", "Get Driver Information", "Get Driver Capabilities",
    "Set Communication Timeout", "Get Communication Timeout", "List Connections",
    "Select Connection", "Get Active Connection", "Get Driver Capability Model",
    "Get Driver Capability", "Find Driver Capabilities", "Get Driver Features",
    "Refresh Driver Capabilities", "Validate Driver Capabilities",
    "Get Driver Configuration Schema", "Get Driver Default Configuration",
    "Get Driver Configuration", "Validate Driver Configuration",
    "Import Driver Configuration", "Export Driver Configuration",
    "Save Driver Configuration", "Load Driver Configuration",
    "List Driver Configuration Profiles", "Delete Driver Configuration Profile",
    "Reset Driver Configuration", "Set Raw I/O Enabled",
})

ALIAS_OF.update({
    "Connect DMM": "Connect",
    "Disconnect DMM": "Disconnect",
    "Close DMM": "Disconnect",
    "Close All DMMs": "Disconnect All",
    "Select DMM": "Select Connection",
    "Get Active DMM Alias": "Get Active Connection",
    "Identify DMM": "Get Identity",
    "Read DMM Error": "Get Device Error",
    "Get DMM Error Queue": "Get All Device Errors",
    "DMM Error Queue Should Be Empty": "Device Error Queue Should Be Empty",
    "Write DMM Command": "Write Raw Command",
    "Query DMM Command": "Query Raw Command",
})

OPEN = [{"keyword": "Open Simulated DMM", "arguments": ["alias=dut", "reading=12.0"]}]
MEASURED = OPEN + [{"keyword": "Measure DC Voltage", "arguments": [10, 10, "alias=dut"]}]
CONFIGURED = OPEN + [{"keyword": "Configure DC Voltage", "arguments": [10, 10, "ON", "alias=dut"]}]
BUS_WAITING = CONFIGURED + [
    {"keyword": "Set DMM Trigger Source", "arguments": ["BUS", "alias=dut"]},
    {"keyword": "Initiate DMM Measurement", "arguments": ["alias=dut"]},
]
BUS_TRIGGERED = BUS_WAITING + [
    {"keyword": "Send DMM Bus Trigger", "arguments": ["alias=dut"]},
]



def _postprocess_v2604(vector: dict[str, Any], name: str) -> dict[str, Any]:
    """Add vectors for canonical RFDS-002/013/014 calls."""
    vector["canonical_keyword"] = ALIAS_OF.get(name, name)
    vector["expected_return"]["type"] = RETURN_TYPES.get(name, "null")
    vector["device_facing"] = name not in NON_DEVICE
    vector["risk_class"] = "R2" if name in {
        "Reset Device", "Write Raw Command", "Query Raw Command", "Read Raw Response",
        "Write DMM Command", "Query DMM Command",
    } else ("R1" if vector["device_facing"] else "R0")

    if name == "Connect":
        vector.update({
            "factory": "visa",
            "arguments": ["GPIB0::22::INSTR", "dut", 10.0, "transport=VISA"],
            "expected_outbound": {"contains_in_order": ["*IDN?", "SYSTem:VERSion?", "SYSTem:ERRor?", "*CLS", "*IDN?"]},
            "expected_inbound": {"response_required": True},
            "expected_return": {"type": "dictionary", "required_keys": ["alias", "resource", "connected", "communication_ok", "transport", "identity", "timeout_s", "state", "simulated"]},
        })
    elif name == "Disconnect":
        vector.update({
            "factory": "serial",
            "setup_calls": [{"keyword": "Open DMM Via Serial", "arguments": ["COM1", "alias=dut", "local_on_close=True"]}],
            "arguments": ["dut"],
            "expected_outbound": {"contains": ["SYSTem:LOCal"]},
            "expected_inbound": {"no_response": True},
        })
    elif name == "Is Connected":
        vector.update({"setup_calls": OPEN, "arguments": ["dut"], "expected_outbound": {"none": True}, "expected_return": {"type": "boolean", "exact": True}})
    elif name == "Get Connection State":
        vector.update({"setup_calls": OPEN, "arguments": ["dut", True], "expected_outbound": {"contains": ["*IDN?"]}, "expected_inbound": {"response_required": True}, "expected_return": {"type": "dictionary", "required_keys": ["alias", "resource", "connected", "communication_ok", "transport", "identity", "timeout_s", "state", "simulated"]}})
    elif name == "Check Communication":
        vector.update({"setup_calls": OPEN, "arguments": ["dut"], "expected_outbound": {"contains": ["*IDN?"]}, "expected_inbound": {"response_required": True}, "expected_return": {"type": "boolean", "exact": True}})
    elif name == "Get Identity":
        vector.update({"setup_calls": OPEN, "arguments": ["dut", True], "expected_outbound": {"contains": ["*IDN?"]}, "expected_inbound": {"response_required": True}, "expected_return": {"type": "string", "contains": "34401A"}})
    elif name == "Get Driver Information":
        vector.update({"expected_outbound": {"none": True}, "expected_return": {"type": "dictionary", "required_keys": ["name", "package_version", "api_version", "api_spec", "api_spec_version", "robot_framework_min_version", "python_min_version", "library_scope", "transport_types", "capability_ids", "simulation_supported", "identity_source"]}})
    elif name == "Get Driver Capabilities":
        vector.update({"expected_outbound": {"none": True}, "expected_return": {"type": "list", "minimum_length": 1}})
    elif name == "Set Communication Timeout":
        vector.update({"setup_calls": OPEN, "arguments": [7.5, "dut"], "expected_outbound": {"none": True}, "expected_return": {"type": "float", "exact": 7.5}})
    elif name == "Get Communication Timeout":
        vector.update({"setup_calls": OPEN + [{"keyword": "Set Communication Timeout", "arguments": [7.5, "dut"]}], "arguments": ["dut"], "expected_outbound": {"none": True}, "expected_return": {"type": "float", "exact": 7.5}})
    elif name == "List Connections":
        vector.update({"setup_calls": OPEN, "expected_outbound": {"none": True}, "expected_return": {"type": "list", "minimum_length": 1}})
    elif name == "Select Connection":
        vector.update({"setup_calls": OPEN + [{"keyword": "Open Simulated DMM", "arguments": ["alias=second", "reading=13"]}], "arguments": ["dut"], "expected_outbound": {"none": True}, "expected_return": {"type": "dictionary", "required_keys": ["alias", "connected"]}})
    elif name == "Disconnect All":
        vector.update({"factory": "serial", "setup_calls": [{"keyword": "Open DMM Via Serial", "arguments": ["COM1", "alias=dut", "local_on_close=True"]}], "expected_outbound": {"contains": ["SYSTem:LOCal"]}})
    elif name == "Get Active Connection":
        vector.update({"setup_calls": OPEN, "expected_outbound": {"none": True}, "expected_return": {"type": "string", "exact": "dut"}})
    elif name == "Get Device Error":
        vector.update({"setup_calls": OPEN, "arguments": ["dut"], "expected_outbound": {"contains": ["SYSTem:ERRor?"]}, "expected_inbound": {"response_required": True}, "expected_return": {"type": "dictionary", "required_keys": ["code", "message", "raw"]}})
    elif name == "Get All Device Errors":
        vector.update({"setup_calls": OPEN, "arguments": [5, "dut"], "expected_outbound": {"contains": ["SYSTem:ERRor?"]}, "expected_inbound": {"response_required": True}, "expected_return": {"type": "list", "minimum_length": 1}})
    elif name in {"Clear Device Errors", "Device Error Queue Should Be Empty"}:
        vector.update({"setup_calls": OPEN, "arguments": ["dut"], "expected_outbound": {"contains": ["SYSTem:ERRor?"]}, "expected_inbound": {"response_required": True}})
        if name == "Clear Device Errors":
            vector["expected_outbound"] = {"contains_in_order": ["*CLS", "SYSTem:ERRor?"]}
    elif name == "Reset Device":
        vector.update({"setup_calls": OPEN, "arguments": ["dut", False], "expected_outbound": {"contains": ["*RST"]}, "expected_return": {"type": "dictionary", "required_keys": ["reset_type", "ready", "elapsed_s", "settings_cleared"]}})
    elif name == "Get Driver Capability Model":
        vector.update({"arguments": ["static"], "expected_outbound": {"none": True}, "expected_return": {"type": "dictionary", "required_keys": ["schema", "driver", "capabilities", "validation"]}})
    elif name == "Get Driver Capability":
        vector.update({"arguments": ["measure.voltage.dc", "static"], "expected_outbound": {"none": True}, "expected_return": {"type": "dictionary", "required_keys": ["capability_id", "binding", "availability"]}})
    elif name == "Find Driver Capabilities":
        vector.update({"arguments": ["measure.", None, "low", False, "static"], "expected_outbound": {"none": True}, "expected_return": {"type": "list", "minimum_length": 1}})
    elif name == "Get Driver Features":
        vector.update({"arguments": ["static"], "expected_outbound": {"none": True}, "expected_return": {"type": "dictionary", "required_keys": ["measurement_functions", "multi_session"]}})
    elif name == "Refresh Driver Capabilities":
        vector.update({"arguments": ["static"], "expected_outbound": {"none": True}, "expected_return": {"type": "dictionary", "required_keys": ["source", "capabilities"]}})
    elif name == "Validate Driver Capabilities":
        vector.update({"expected_outbound": {"none": True}, "expected_return": {"type": "dictionary", "required_keys": ["valid", "capability_count", "missing_keyword_bindings"]}})
    elif name == "Get Driver Configuration Schema":
        vector.update({"expected_outbound": {"none": True}, "expected_return": {"type": "dictionary", "required_keys": ["$schema", "properties"]}})
    elif name == "Get Driver Default Configuration":
        vector.update({"expected_outbound": {"none": True}, "expected_return": {"type": "dictionary", "required_keys": ["rfds014_version", "settings"]}})
    elif name == "Get Driver Configuration":
        vector.update({"arguments": ["EFFECTIVE", None, True, True], "expected_outbound": {"none": True}, "expected_return": {"type": "dictionary", "required_keys": ["profile", "settings", "metadata"]}})
    elif name == "Validate Driver Configuration":
        vector.update({"arguments": ["config/default.json", True], "expected_outbound": {"none": True}, "expected_return": {"type": "dictionary", "required_keys": ["valid", "configuration"]}})
    elif name == "Import Driver Configuration":
        vector.update({"arguments": ["config/default.json", True, True], "expected_outbound": {"none": True}, "expected_return": {"type": "dictionary", "required_keys": ["settings"]}})
    elif name == "Export Driver Configuration":
        vector.update({"arguments": [None, 2], "expected_outbound": {"none": True}, "expected_return": {"type": "string", "contains": "rf_hp34401a.configuration"}})
    elif name == "Save Driver Configuration":
        vector.update({"profile_temp": True, "arguments": ["conformance", True], "expected_outbound": {"none": True}, "expected_return": {"type": "string", "contains": "conformance.json"}})
    elif name == "Load Driver Configuration":
        vector.update({"profile_temp": True, "setup_calls": [{"keyword": "Save Driver Configuration", "arguments": ["conformance", True]}], "arguments": ["conformance", False], "expected_outbound": {"none": True}, "expected_return": {"type": "dictionary", "required_keys": ["settings"]}})
    elif name == "List Driver Configuration Profiles":
        vector.update({"profile_temp": True, "setup_calls": [{"keyword": "Save Driver Configuration", "arguments": ["conformance", True]}], "expected_outbound": {"none": True}, "expected_return": {"type": "list", "minimum_length": 1}})
    elif name == "Delete Driver Configuration Profile":
        vector.update({"profile_temp": True, "setup_calls": [{"keyword": "Save Driver Configuration", "arguments": ["conformance", True]}], "arguments": ["conformance"], "expected_outbound": {"none": True}})
    elif name == "Reset Driver Configuration":
        vector.update({"expected_outbound": {"none": True}, "expected_return": {"type": "dictionary", "required_keys": ["settings", "metadata"]}})
    elif name == "Set Raw I/O Enabled":
        vector.update({"arguments": [True], "expected_outbound": {"none": True}, "expected_return": {"type": "boolean", "exact": True}})
    elif name in {"Write Raw Command", "Write DMM Command"}:
        vector.update({"setup_calls": OPEN + [{"keyword": "Set Raw I/O Enabled", "arguments": [True]}], "arguments": ["*CLS", "dut"], "expected_outbound": {"contains": ["*CLS"]}})
    elif name in {"Query Raw Command", "Query DMM Command"}:
        args = ["*IDN?", "dut", 10.0] if name == "Query Raw Command" else ["*IDN?", "dut"]
        vector.update({"setup_calls": OPEN + [{"keyword": "Set Raw I/O Enabled", "arguments": [True]}], "arguments": args, "expected_outbound": {"contains": ["*IDN?"]}, "expected_inbound": {"response_required": True}, "expected_return": {"type": "string", "contains": "34401A"}})
    elif name == "Read Raw Response":
        vector.update({"setup_calls": OPEN + [{"keyword": "Set Raw I/O Enabled", "arguments": [True]}], "arguments": ["dut", 10.0], "expected_outbound": {"none": True}, "expected_inbound": {"no_response": True}, "expected_return": {"type": "string"}})
    return vector

def vector_for(item: dict[str, Any], index: int) -> dict[str, Any]:
    name = item["keyword"]
    vector: dict[str, Any] = {
        "id": f"HP34401A-KW-{index:03d}",
        "keyword": name,
        "canonical_keyword": ALIAS_OF.get(name, name),
        "driver_method": item["driver_method"],
        "device_facing": name not in NON_DEVICE,
        "risk_class": "R1" if name not in NON_DEVICE else "R0",
        "arguments": [],
        "expected_outbound": {"none": True} if name in NON_DEVICE else {},
        "expected_inbound": {"no_response": True},
        "expected_return": {"type": RETURN_TYPES.get(name, "null")},
    }
    if name in {
        "Connect DMM",
        "Open DMM Via VISA",
        "Open DMM Via Serial",
        "Open Simulated DMM",
        "List VISA Resources",
        "Get Active DMM Alias",
        "Get Open DMM Aliases",
        "Close All DMMs",
        "Get DMM Driver Version",
        "Get Robot DMM Library Version",
        "Get Driver Capabilities",
        "Get Driver Metadata",
    }:
        pass
    elif name == "Select DMM":
        vector["setup_calls"] = OPEN + [
            {"keyword": "Open Simulated DMM", "arguments": ["alias=second", "reading=13.0"]}
        ]
        vector["arguments"] = ["dut"]
        vector["expected_return"]["exact"] = "dut"
    elif name == "DMM Should Be Connected":
        vector["setup_calls"] = OPEN
        vector["arguments"] = ["dut"]
    elif name in {"Close DMM", "Disconnect DMM"}:
        vector["factory"] = "serial"
        vector["setup_calls"] = [
            {
                "keyword": "Open DMM Via Serial",
                "arguments": ["COM1", "alias=dut", "local_on_close=True"],
            }
        ]
        vector["arguments"] = ["dut"]
        vector["expected_outbound"] = {"contains": ["SYSTem:LOCal"]}
        vector["expected_inbound"] = {"no_response": True}
    elif name in {
        "Identify DMM",
        "DMM Model Should Be 34401A",
        "Run DMM Self Test",
        "DMM Self Test Should Pass",
        "Get DMM Health",
        "Recover DMM",
        "Clear DMM Status",
        "Read DMM Error",
        "Get DMM Error Queue",
        "DMM Error Queue Should Be Empty",
        "Get DMM Input Terminal",
        "Require DMM Input Terminal",
        "Get DMM State",
        "Get Driver Metadata",
        "Configure DC Voltage",
        "Configure AC Voltage",
        "Configure DC Current",
        "Configure AC Current",
        "Configure 2 Wire Resistance",
        "Configure 4 Wire Resistance",
        "Configure Frequency",
        "Configure Period",
        "Configure Continuity",
        "Configure Diode",
        "Read DMM",
        "Measure DC Voltage",
        "Measure AC Voltage",
        "Measure DC Current",
        "Measure AC Current",
        "Measure 2 Wire Resistance",
        "Measure 4 Wire Resistance",
        "Measure Frequency",
        "Measure Period",
        "Measure Continuity",
        "Measure Diode",
        "Try Read Stable Resistance",
        "Read Stable Resistance",
        "Get Last DMM Reading",
        "Get Last DMM Reading Value",
        "Set DMM Trigger Source",
        "Initiate DMM Measurement",
        "Send DMM Bus Trigger",
        "Fetch DMM Readings",
        "Read DMM Once With Bus Trigger",
        "DMM Reading Should Be Valid",
        "DMM Reading Should Not Be Overload",
        "DMM Reading Should Be Between",
        "DMM Reading Should Be Close To",
        "DMM Reading Should Be Greater Than",
        "DMM Reading Should Be Less Than",
        "DMM Should Have No Errors",
        "Write DMM Command",
        "Query DMM Command",
    }:
        vector["setup_calls"] = OPEN

    if name == "Connect DMM":
        vector["factory"] = "visa"
        vector["arguments"] = ["GPIB0::22::INSTR", "VISA", "dut"]
        vector["expected_outbound"] = {
            "contains_in_order": ["*IDN?", "SYSTem:VERSion?", "SYSTem:ERRor?", "*CLS"]
        }
        vector["expected_inbound"] = {"response_required": True, "raw_contains": ["1991.0"]}
        vector["expected_return"]["exact"] = "dut"
    elif name == "Open DMM Via VISA":
        vector["factory"] = "visa"
        vector["arguments"] = ["GPIB0::22::INSTR", "alias=dut"]
        vector["expected_outbound"] = {
            "contains_in_order": ["*IDN?", "SYSTem:VERSion?", "SYSTem:ERRor?", "*CLS"]
        }
        vector["expected_inbound"] = {"response_required": True, "raw_contains": ["1991.0"]}
        vector["expected_return"]["exact"] = "dut"
    elif name == "Open DMM Via Serial":
        vector["factory"] = "serial"
        vector["arguments"] = ["COM1", "alias=dut", "local_on_close=True"]
        vector["expected_outbound"] = {
            "contains_in_order": [
                "SYSTem:REMote",
                "*IDN?",
                "*IDN?",
                "SYSTem:VERSion?",
                "*CLS",
            ]
        }
        vector["expected_inbound"] = {"response_required": True, "raw_contains": ["1991.0"]}
        vector["expected_return"]["exact"] = "dut"
    elif name == "Open Simulated DMM":
        vector["arguments"] = ["alias=dut", "reading=12.0"]
        vector["expected_outbound"] = {
            "contains_in_order": ["*IDN?", "SYSTem:VERSion?", "SYSTem:ERRor?", "*CLS"]
        }
        vector["expected_inbound"] = {"response_required": True, "raw_contains": ["1991.0"]}
        vector["expected_return"]["exact"] = "dut"
    elif name == "List VISA Resources":
        vector["pyvisa_stub"] = True
        vector["expected_return"]["minimum_length"] = 2
    elif name == "Get Active DMM Alias":
        vector["setup_calls"] = OPEN
        vector["expected_return"]["exact"] = "dut"
    elif name == "Get Open DMM Aliases":
        vector["setup_calls"] = OPEN
        vector["expected_return"]["minimum_length"] = 1
    elif name == "Close All DMMs":
        vector["factory"] = "serial"
        vector["setup_calls"] = [
            {
                "keyword": "Open DMM Via Serial",
                "arguments": ["COM1", "alias=dut", "local_on_close=True"],
            }
        ]
        vector["expected_outbound"] = {"contains": ["SYSTem:LOCal"]}
    elif name == "Identify DMM":
        vector["arguments"] = ["dut"]
        vector["expected_outbound"] = {"contains": ["*IDN?"]}
        vector["expected_inbound"] = {"response_required": True}
        vector["expected_return"]["required_keys"] = ["manufacturer", "model", "serial", "firmware", "raw"]
    elif name == "DMM Model Should Be 34401A":
        vector["arguments"] = ["dut"]
        vector["expected_outbound"] = {"contains": ["*IDN?"]}
        vector["expected_inbound"] = {"response_required": True}
    elif name in {"Run DMM Self Test", "DMM Self Test Should Pass"}:
        vector["arguments"] = ["dut"]
        vector["expected_outbound"] = {"contains": ["*TST?"]}
        vector["expected_inbound"] = {"response_required": True, "raw_contains": ["0"]}
        if name == "Run DMM Self Test":
            vector["expected_return"]["required_keys"] = ["passed", "code", "raw", "message"]
    elif name == "Get DMM Health":
        vector["arguments"] = ["dut"]
        vector["expected_outbound"] = {"contains": ["SYSTem:ERRor?"]}
        vector["expected_inbound"] = {"response_required": True}
        vector["expected_return"]["required_keys"] = ["connected", "error_queue_clean", "state"]
    elif name == "Recover DMM":
        vector["arguments"] = ["dut"]
        vector["expected_outbound"] = {"contains": ["SYSTem:ERRor?"], "clear_count_min": 1}
        vector["expected_inbound"] = {"response_required": True}
        vector["expected_return"]["required_keys"] = ["succeeded", "actions", "state"]
    elif name == "Clear DMM Status":
        vector["arguments"] = ["dut"]
        vector["expected_outbound"] = {"contains": ["*CLS"]}
    elif name == "Read DMM Error":
        vector["arguments"] = ["dut"]
        vector["expected_outbound"] = {"contains": ["SYSTem:ERRor?"]}
        vector["expected_inbound"] = {"response_required": True}
        vector["expected_return"]["required_keys"] = ["code", "message", "raw"]
    elif name == "Get DMM Error Queue":
        vector["arguments"] = [5, "dut"]
        vector["expected_outbound"] = {"contains": ["SYSTem:ERRor?"]}
        vector["expected_inbound"] = {"response_required": True}
        vector["expected_return"]["minimum_length"] = 1
    elif name in {"DMM Error Queue Should Be Empty", "DMM Should Have No Errors"}:
        vector["arguments"] = ["dut"] if name.startswith("DMM Error") else ["conformance", "dut"]
        vector["expected_outbound"] = {"contains": ["SYSTem:ERRor?"]}
        vector["expected_inbound"] = {"response_required": True}
    elif name in {"Get DMM Input Terminal", "Require DMM Input Terminal"}:
        vector["arguments"] = ["dut"] if name.startswith("Get") else ["FRONT", "dut"]
        vector["expected_outbound"] = {"contains": ["ROUTe:TERMinals?"]}
        vector["expected_inbound"] = {"response_required": True, "raw_contains": ["FRONT"]}
        if name.startswith("Get"):
            vector["expected_return"]["exact"] = "FRONT"
    elif name == "Get DMM State":
        vector["arguments"] = ["dut"]
    elif name == "Get DMM Driver Version":
        vector["expected_return"]["exact"] = "1.2.8"
    elif name == "Get Robot DMM Library Version":
        vector["expected_return"]["exact"] = "26.07"
    elif name == "Get Driver Capabilities":
        vector["expected_return"]["minimum_length"] = 1
    elif name == "Get Driver Metadata":
        vector["arguments"] = ["dut"]
        vector["expected_return"]["required_keys"] = ["driver_version", "core_driver_version", "state"]
    else:
        configure = {
            "Configure DC Voltage": ([10, 10, "ON", "dut"], ["CONFigure:VOLTage:DC 10,DEF", "SENSe:VOLTage:DC:NPLCycles 10"]),
            "Configure AC Voltage": ([10, 20, "dut"], ["CONFigure:VOLTage:AC 10,DEF", "SENSe:DETector:BANDwidth 20"]),
            "Configure DC Current": ([1, 10, "ON", "dut"], ["CONFigure:CURRent:DC 1,DEF", "SENSe:CURRent:DC:NPLCycles 10"]),
            "Configure AC Current": ([1, 20, "dut"], ["CONFigure:CURRent:AC 1,DEF", "SENSe:DETector:BANDwidth 20"]),
            "Configure 2 Wire Resistance": ([1000, 10, "ON", "dut"], ["CONFigure:RESistance 1000,DEF", "SENSe:RESistance:NPLCycles 10"]),
            "Configure 4 Wire Resistance": ([1000, 10, "ON", "dut"], ["CONFigure:FRESistance 1000,DEF", "SENSe:FRESistance:NPLCycles 10"]),
            "Configure Frequency": ([10, 0.1, "dut"], ["CONFigure:FREQuency 10,DEF", "SENSe:FREQuency:APERture 0.1"]),
            "Configure Period": ([10, 0.1, "dut"], ["CONFigure:PERiod 10,DEF", "SENSe:PERiod:APERture 0.1"]),
            "Configure Continuity": (["dut"], ["CONFigure:CONTinuity"]),
            "Configure Diode": (["dut"], ["CONFigure:DIODe"]),
        }
        measurements = {
            "Measure DC Voltage": ([10, 10, "dut"], "CONFigure:VOLTage:DC 10,DEF"),
            "Measure AC Voltage": ([10, 20, "dut"], "CONFigure:VOLTage:AC 10,DEF"),
            "Measure DC Current": ([1, 10, "dut"], "CONFigure:CURRent:DC 1,DEF"),
            "Measure AC Current": ([1, 20, "dut"], "CONFigure:CURRent:AC 1,DEF"),
            "Measure 2 Wire Resistance": ([1000, 10, "dut"], "CONFigure:RESistance 1000,DEF"),
            "Measure 4 Wire Resistance": ([1000, 10, "dut"], "CONFigure:FRESistance 1000,DEF"),
            "Measure Frequency": ([10, 0.1, "dut"], "CONFigure:FREQuency 10,DEF"),
            "Measure Period": ([10, 0.1, "dut"], "CONFigure:PERiod 10,DEF"),
            "Measure Continuity": (["dut"], "CONFigure:CONTinuity"),
            "Measure Diode": (["dut"], "CONFigure:DIODe"),
        }
        if name in configure:
            vector["arguments"], operations = configure[name]
            vector["expected_outbound"] = {"contains_in_order": operations}
        elif name == "Read DMM":
            vector["setup_calls"] = CONFIGURED
            vector["arguments"] = ["dut"]
            vector["expected_outbound"] = {"contains_in_order": ["TRIGger:SOURce IMMediate", "TRIGger:COUNt 1", "SAMPle:COUNt 1", "READ?"]}
            vector["expected_inbound"] = {"response_required": True, "raw_contains": ["12.0"]}
        elif name in measurements:
            vector["arguments"], operation = measurements[name]
            vector["expected_outbound"] = {"contains_in_order": [operation, "READ?"]}
            vector["expected_inbound"] = {"response_required": True, "raw_contains": ["12.0"]}
        elif name in {"Try Read Stable Resistance", "Read Stable Resistance"}:
            vector["arguments"] = [
                "expected_ohm=12",
                "range_value=100",
                "nplc=0.02",
                "final_nplc=None",
                "min_settle=0 s",
                "max_wait=300 ms",
                "sample_interval=1 ms",
                "window_size=3",
                "alias=dut",
            ]
            vector["expected_outbound"] = {"contains": ["CONFigure:RESistance 100,DEF", "READ?"]}
            vector["expected_inbound"] = {"response_required": True, "raw_contains": ["12.0"]}
            if name.startswith("Try"):
                vector["expected_return"]["required_keys"] = ["stable", "value", "samples", "elapsed_s"]
        elif name in {"Get Last DMM Reading", "Get Last DMM Reading Value", "DMM Reading Should Be Valid", "DMM Reading Should Not Be Overload", "DMM Reading Should Be Between", "DMM Reading Should Be Close To", "DMM Reading Should Be Greater Than", "DMM Reading Should Be Less Than"}:
            vector["setup_calls"] = MEASURED
            if name == "Get Last DMM Reading":
                vector["arguments"] = ["dut"]
                vector["expected_return"]["required_keys"] = ["function", "value", "unit", "is_valid", "alias"]
            elif name == "Get Last DMM Reading Value":
                vector["arguments"] = ["dut"]
                vector["expected_return"]["exact"] = 12.0
            elif name in {"DMM Reading Should Be Valid", "DMM Reading Should Not Be Overload"}:
                vector["arguments"] = ["dut"]
            elif name == "DMM Reading Should Be Between":
                vector["arguments"] = [11, 13, "dut"]
            elif name == "DMM Reading Should Be Close To":
                vector["arguments"] = [12, 0.1, 0, "dut"]
            elif name == "DMM Reading Should Be Greater Than":
                vector["arguments"] = [11, "dut"]
            elif name == "DMM Reading Should Be Less Than":
                vector["arguments"] = [13, "dut"]
        elif name == "Stable Resistance Should Be Between":
            vector["arguments"] = ["$STABLE_RESULT", 900, 1100]
        elif name == "Set DMM Trigger Source":
            vector["arguments"] = ["BUS", "dut"]
            vector["expected_outbound"] = {"contains": ["TRIGger:SOURce BUS"]}
        elif name == "Initiate DMM Measurement":
            vector["setup_calls"] = CONFIGURED
            vector["arguments"] = ["dut"]
            vector["expected_outbound"] = {"contains_in_order": ['DATA:FEED RDG_STORE,"CALC"', "INITiate"]}
        elif name == "Send DMM Bus Trigger":
            vector["setup_calls"] = CONFIGURED + [{"keyword": "Set DMM Trigger Source", "arguments": ["BUS", "alias=dut"]}]
            vector["arguments"] = ["dut"]
            vector["expected_outbound"] = {"contains": ["*TRG"]}
        elif name == "Fetch DMM Readings":
            vector["setup_calls"] = BUS_TRIGGERED
            vector["arguments"] = ["dut"]
            vector["expected_outbound"] = {"contains": ["FETCh?"]}
            vector["expected_inbound"] = {"response_required": True, "raw_contains": ["12.0"]}
            vector["expected_return"]["minimum_length"] = 1
        elif name == "Read DMM Once With Bus Trigger":
            vector["setup_calls"] = CONFIGURED
            vector["arguments"] = ["dut"]
            vector["expected_outbound"] = {"contains_in_order": ["TRIGger:SOURce BUS", "TRIGger:COUNt 1", "SAMPle:COUNt 1", 'DATA:FEED RDG_STORE,"CALC"', "INITiate", "*TRG", "FETCh?"], "forbidden": ["READ?"]}
            vector["expected_inbound"] = {"response_required": True, "raw_contains": ["12.0"]}
        elif name == "Write DMM Command":
            vector["arguments"] = ["*CLS", "dut"]
            vector["expected_outbound"] = {"contains": ["*CLS"]}
        elif name == "Query DMM Command":
            vector["arguments"] = ["*IDN?", "dut"]
            vector["expected_outbound"] = {"contains": ["*IDN?"]}
            vector["expected_inbound"] = {"response_required": True}
            vector["expected_return"]["contains"] = "34401A"
    return _postprocess_v2604(vector, name)


def main() -> None:
    surface = source_surface()
    vectors = [vector_for(item, index) for index, item in enumerate(surface, 1)]
    inventory = {
        "rfds019_version": "1.1",
        "driver": "rf_hp34401a.Hp34401ALibrary",
        "driver_version": "26.07",
        "keywords": [
            {
                "keyword": item["keyword"],
                "canonical_keyword": ALIAS_OF.get(item["keyword"], item["keyword"]),
                "aliases": [],
                "driver_method": item["driver_method"],
                "arguments": item["arguments"],
                "return_type": RETURN_TYPES.get(item["keyword"], "null"),
                "device_facing": item["keyword"] not in NON_DEVICE,
                "protocol_vector": vector["id"],
                "execution_status": "NOT RUN",
            }
            for item, vector in zip(surface, vectors)
        ],
    }
    errors = {
        "protocol_error_vectors": [
            {
                "id": "HP34401A-ERR-001",
                "keyword": "Query DMM Command",
                "setup_calls": OPEN,
                "transport_mutation": {"alias": "dut", "timeout_on": ["*IDN?"]},
                "arguments": ["*IDN?", "dut"],
                "expected_error_pattern": "*timeout*",
                "remove_timeout_on": ["*IDN?"],
                "recovery": {
                    "keyword": "Identify DMM",
                    "arguments": ["dut"],
                    "expected_return": {"type": "dictionary", "required_keys": ["model"]},
                },
            },
            {
                "id": "HP34401A-ERR-002",
                "keyword": "Measure DC Voltage",
                "setup_calls": OPEN,
                "transport_mutation": {"alias": "dut", "responses": {"READ?": "MALFORMED"}},
                "arguments": [10, 10, "dut"],
                "expected_error_pattern": "*parse*",
                "recovery_responses": {"READ?": "12.0"},
                "recovery": {
                    "keyword": "Measure DC Voltage",
                    "arguments": [10, 10, "dut"],
                    "expected_return": {"type": "float", "exact": 12.0},
                },
            },
            {
                "id": "HP34401A-ERR-003",
                "keyword": "DMM Error Queue Should Be Empty",
                "setup_calls": OPEN,
                "transport_mutation": {"alias": "dut", "error_queue": ['-100,"Command error"']},
                "arguments": ["dut"],
                "expected_error_pattern": "*DMM error queue is not empty*",
                "recovery": {
                    "keyword": "Identify DMM",
                    "arguments": ["dut"],
                    "expected_return": {"type": "dictionary", "required_keys": ["model"]},
                },
            },
            {
                "id": "HP34401A-ERR-004",
                "keyword": "Write DMM Command",
                "setup_calls": OPEN,
                "arguments": ["CALibration:SECure:STATe OFF", "dut"],
                "expected_error_pattern": "*Calibration commands are blocked*",
                "recovery": {
                    "keyword": "Identify DMM",
                    "arguments": ["dut"],
                    "expected_return": {"type": "dictionary", "required_keys": ["model"]},
                },
            },
        ]
    }
    doc = {"rfds019_version": "1.1", "vectors": vectors, **errors}
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "keyword_inventory.yaml").write_text(
        yaml.safe_dump(inventory, sort_keys=False, width=120), encoding="utf-8"
    )
    (DATA / "protocol_vectors.yaml").write_text(
        yaml.safe_dump(doc, sort_keys=False, width=120), encoding="utf-8"
    )
    print(f"Generated {len(surface)} keyword entries and {len(vectors)} vectors")


if __name__ == "__main__":
    main()
