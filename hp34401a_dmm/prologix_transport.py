"""Optional/experimental Prologix USB-GPIB transport (spec section 21.4, Phase 3).

Per spec section 2.3, optional features that are not implemented must raise a
clear NotImplementedError rather than ship placeholder-only code.
"""

from __future__ import annotations

from .config import SerialRs232Config
from .transports import BaseTransport


class PrologixUsbGpibTransport(BaseTransport):
    """Not yet implemented (Phase 3, experimental)."""

    def __init__(self, *args: object, **kwargs: object) -> None:  # noqa: D401
        raise NotImplementedError(
            "PrologixUsbGpibTransport is a Phase 3 experimental feature and is not "
            "implemented in this build. Use SerialRs232Transport or VisaGpibTransport. "
            "When implemented it must configure Prologix controller mode/address/auto-read/"
            "EOI/EOS settings and never interleave controller commands with instrument SCPI."
        )
