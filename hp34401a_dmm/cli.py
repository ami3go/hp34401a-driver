"""Command-line interface (spec section 27).

Import-safe: ``hp34401a --help`` and argument parsing require no hardware and no
pyserial/pyvisa.  A transport is only constructed when a command actually runs.
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Sequence

from .config import DriverConfig, SerialRs232Config, VisaGpibConfig
from .enums import AutoRange, Nplc
from .errors import Hp34401AError


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="hp34401a", description="HP 34401A production DMM driver")
    p.add_argument("--verbose", "-v", action="store_true", help="enable debug logging")
    sub = p.add_subparsers(dest="command", required=True)

    def add_transport(sp: argparse.ArgumentParser) -> None:
        g = sp.add_mutually_exclusive_group(required=True)
        g.add_argument("--serial", metavar="PORT", help="RS-232 COM port, e.g. COM3 or /dev/ttyUSB0")
        g.add_argument("--visa", metavar="RESOURCE", help="VISA resource, e.g. GPIB0::22::INSTR")
        sp.add_argument("--baud", type=int, default=9600)
        sp.add_argument("--parity", choices=["none", "even", "odd"], default="none")
        sp.add_argument("--data-bits", type=int, default=8)

    sp = sub.add_parser("identify", help="query *IDN?")
    add_transport(sp)

    sp = sub.add_parser("self-test", help="run *TST?")
    add_transport(sp)

    sp = sub.add_parser("error-drain", help="drain the error queue")
    add_transport(sp)

    sp = sub.add_parser("measure", help="single measurement")
    sp.add_argument(
        "function",
        choices=["dc-voltage", "ac-voltage", "dc-current", "resistance-2w", "resistance-4w"],
    )
    add_transport(sp)
    sp.add_argument("--range", type=float, default=None, help="manual range; omit for autorange")
    sp.add_argument("--nplc", type=float, default=10.0)

    return p


def _make_driver(args: argparse.Namespace):
    from .driver import Hp34401A

    dcfg = DriverConfig(raw_traffic_log=args.verbose)
    if getattr(args, "serial", None):
        scfg = SerialRs232Config(
            port=args.serial, baudrate=args.baud, parity=args.parity, data_bits=args.data_bits,
            stop_bits=2,
        )
        return Hp34401A.from_serial(scfg, dcfg)
    vcfg = VisaGpibConfig(resource=args.visa)
    return Hp34401A.from_visa_gpib(vcfg, dcfg)


def _range_arg(value: float | None) -> float | AutoRange:
    return AutoRange.AUTO if value is None else value


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    try:
        driver = _make_driver(args)
    except (Hp34401AError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    try:
        with driver:
            return _dispatch(args, driver)
    except (Hp34401AError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _dispatch(args: argparse.Namespace, driver) -> int:
    if args.command == "identify":
        ident = driver.identify()
        print(f"{ident.manufacturer} {ident.model} serial={ident.serial} fw={ident.firmware}")
        return 0
    if args.command == "self-test":
        result = driver.self_test()
        print(f"self-test: {'PASS' if result.passed else 'FAIL'} (code={result.code})")
        return 0 if result.passed else 1
    if args.command == "error-drain":
        errors = driver.drain_error_queue()
        real = [e for e in errors if not e.is_no_error]
        if not real:
            print("error queue clean")
        else:
            for e in real:
                print(f"{e.code}: {e.message}")
        return 0
    if args.command == "measure":
        nplc = _nearest_nplc(args.nplc)
        rng = _range_arg(args.range)
        method = {
            "dc-voltage": lambda: driver.measure_dc_voltage(rng, nplc),
            "ac-voltage": lambda: driver.measure_ac_voltage(rng),
            "dc-current": lambda: driver.measure_dc_current(rng, nplc),
            "resistance-2w": lambda: driver.measure_2wire_resistance(rng, nplc),
            "resistance-4w": lambda: driver.measure_4wire_resistance(rng, nplc),
        }[args.function]
        reading = method()
        if reading.is_overload:
            print("OVERLOAD")
            return 1
        print(f"{reading.value} {reading.unit}")
        return 0
    return 2


def _nearest_nplc(value: float) -> Nplc:
    options = list(Nplc)
    return min(options, key=lambda n: abs(n.value - value))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
