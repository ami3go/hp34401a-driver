"""Compatibility wrapper for the standalone HP 34401A GUI package.

The actual GUI implementation is in ``hp34401a_gui.app``. This wrapper is
kept so old commands/imports keep working and so running this file directly
from an IDE does not fail with "attempted relative import with no known parent
package".
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from hp34401a_gui.app import main

__all__ = ["main"]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
