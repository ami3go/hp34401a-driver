"""Immutable configuration dataclasses (spec sections 8.2, 17, incorporating R1/R4/R8)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .enums import AutoRange, AcFilterHz, Nplc


@dataclass(frozen=True, slots=True)
class SerialRs232Config:
    port: str
    baudrate: int = 9600
    parity: Literal["none", "even", "odd"] = "none"
    data_bits: int = 8
    stop_bits: int = 2
    timeout_s: float = 10.0
    write_timeout_s: float = 5.0
    use_dtr_dsr: bool = True
    require_remote_on_connect: bool = True
    send_local_on_close: bool = False
    recover_on_connect: bool = False
    encoding: str = "ascii"
    read_termination: str = "\n"
    write_termination: str = "\n"

    def __post_init__(self) -> None:
        # Validate the supported parity/data-bit combinations (spec section 21.2).
        valid = {("none", 8), ("even", 7), ("odd", 7)}
        if (self.parity, self.data_bits) not in valid:
            raise ValueError(
                f"Unsupported parity/data-bit combination: {self.parity}/{self.data_bits}. "
                "The 34401A supports none/8, even/7, odd/7."
            )
        if self.baudrate not in (300, 600, 1200, 2400, 4800, 9600):
            raise ValueError(f"Unsupported baud rate: {self.baudrate}")
        if self.stop_bits != 2:
            raise ValueError("The 34401A uses a fixed 2 stop bits.")


@dataclass(frozen=True, slots=True)
class VisaGpibConfig:
    resource: str
    timeout_s: float = 10.0
    read_termination: str = "\n"
    write_termination: str = "\n"
    clear_on_connect: bool = True
    visa_library: str | None = None


@dataclass(frozen=True, slots=True)
class DriverConfig:
    reset_on_connect: bool = False
    clear_status_on_connect: bool = True
    verify_identity_on_connect: bool = True
    drain_error_queue_on_connect: bool = True
    default_timeout_s: float = 10.0
    long_measurement_timeout_s: float = 60.0
    self_test_timeout_s: float = 30.0  # R8
    line_frequency_hz: Literal[50, 60] = 50  # R4: timeout-estimation only
    auto_reconnect: bool = False  # explicit Phase-1 default: no hidden reconnects
    max_reconnect_attempts: int = 3
    retry_queries: bool = True  # safe timeout retry for explicitly retryable queries
    max_query_retries: int = 1
    query_retry_delay_s: float = 0.05
    retry_all_queries_on_timeout: bool = False  # expert mode; READ? still handled by read_once()
    retry_writes: bool = False
    allow_calibration_commands: bool = False
    thread_safe: bool = True
    raw_traffic_log: bool = False

    def __post_init__(self) -> None:
        if self.default_timeout_s <= 0:
            raise ValueError("default_timeout_s must be > 0")
        if self.long_measurement_timeout_s <= 0:
            raise ValueError("long_measurement_timeout_s must be > 0")
        if self.self_test_timeout_s <= 0:
            raise ValueError("self_test_timeout_s must be > 0")
        if self.max_reconnect_attempts < 0:
            raise ValueError("max_reconnect_attempts must be >= 0")
        if self.max_query_retries < 0:
            raise ValueError("max_query_retries must be >= 0")
        if self.query_retry_delay_s < 0:
            raise ValueError("query_retry_delay_s must be >= 0")


@dataclass(frozen=True, slots=True)
class StabilityProfile:
    expected_ohm: float | None = None
    range_ohm: float | AutoRange = AutoRange.AUTO
    nplc: Nplc = Nplc.PLC10
    final_nplc: Nplc | None = Nplc.PLC100
    min_settle_s: float = 0.5
    max_wait_s: float = 20.0
    sample_interval_s: float = 0.2
    window_size: int = 5
    max_stdev_ohm: float | None = None
    max_relative_stdev: float | None = 0.0005
    max_slope_relative_per_s: float | None = 0.0005
    reject_overload: bool = True
    four_wire: bool = False

    def __post_init__(self) -> None:
        if self.expected_ohm is not None and self.expected_ohm <= 0:
            raise ValueError("expected_ohm must be positive when provided")
        if isinstance(self.range_ohm, (int, float)) and self.range_ohm <= 0:
            raise ValueError("range_ohm must be positive or AutoRange")
        if self.min_settle_s < 0:
            raise ValueError("min_settle_s must be >= 0")
        if self.max_wait_s <= 0:
            raise ValueError("max_wait_s must be > 0")
        if self.sample_interval_s <= 0:
            raise ValueError("sample_interval_s must be > 0")
        if self.window_size < 2:
            raise ValueError("window_size must be >= 2")
        if self.max_stdev_ohm is not None and self.max_stdev_ohm < 0:
            raise ValueError("max_stdev_ohm must be >= 0 when provided")
        if self.max_relative_stdev is not None and self.max_relative_stdev < 0:
            raise ValueError("max_relative_stdev must be >= 0 when provided")
        if (
            self.max_slope_relative_per_s is not None
            and self.max_slope_relative_per_s < 0
        ):
            raise ValueError("max_slope_relative_per_s must be >= 0 when provided")


@dataclass(frozen=True, slots=True)
class ContinuousLoggerConfig:
    interval_s: float = 1.0
    duration_s: float | None = None  # None = run until stopped
    csv_path: str | None = None
    jsonl_path: str | None = None
    fsync: bool = False
    heartbeat_every: int = 60
    max_gap_s: float | None = None
