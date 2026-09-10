#!/usr/bin/env python3
"""Run RFDS-019 call/protocol conformance and preserve timestamped evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run RFDS-019 v1.1 conformance against the approved FakeTransport profile."
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=ROOT / "results" / "call_protocol_conformance" / "hp34401a",
    )
    parser.add_argument(
        "--profile",
        choices=["simulator"],
        default="simulator",
        help="Only the deterministic software profile is unattended; real hardware uses tests/hil.",
    )
    args = parser.parse_args()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = args.output_root.resolve() / timestamp
    destination.mkdir(parents=True, exist_ok=False)
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT) + os.pathsep + environment.get("PYTHONPATH", "")
    command = [
        sys.executable,
        "-m",
        "robot",
        "--outputdir",
        str(destination),
        "--variable",
        f"CONFORMANCE_OUTPUT_DIR:{destination}",
        str(ROOT / "tests" / "conformance" / "driver_call_protocol_conformance.robot"),
    ]
    print("+", " ".join(command), flush=True)
    completed = subprocess.run(command, cwd=ROOT, env=environment, check=False)
    print(f"RFDS-019 results: {destination}")
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
