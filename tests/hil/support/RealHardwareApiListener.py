"""Robot Framework listener that records every public driver keyword to disk."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_SUPPORT_DIR = Path(__file__).resolve().parent
if str(_SUPPORT_DIR) not in sys.path:
    sys.path.insert(0, str(_SUPPORT_DIR))

from coverage_state import configured_state_path, merge_record

ROBOT_LISTENER_API_VERSION = 3
_ROOT = Path(__file__).resolve().parents[3]
_PUBLIC_API = json.loads((_ROOT / "api" / "public_api.yaml").read_text(encoding="utf-8"))
_KEYWORDS = {item["name"]: item for item in _PUBLIC_API["keywords"]}


def end_keyword(data: Any, result: Any) -> None:
    """Persist one public keyword result at the Robot execution boundary."""
    name = str(getattr(result, "name", getattr(data, "name", "")))
    candidate = name
    if candidate not in _KEYWORDS and "." in candidate:
        candidate = candidate.rsplit(".", 1)[-1]
    if candidate not in _KEYWORDS:
        return
    status = str(getattr(result, "status", "UNKNOWN")).upper()
    item = _KEYWORDS[candidate]
    merge_record(
        configured_state_path(),
        {
            "keyword": candidate,
            "canonical_keyword": item["canonical_name"],
            "status": status,
            "message": str(getattr(result, "message", "")),
            "elapsed_ms": int(getattr(result, "elapsedtime", 0) or 0),
            "device_facing": bool(item["device_facing"]),
            "protocol_vector": item.get("protocol_vector"),
            "evidence": "output.xml/log.html/report.html",
        },
    )
