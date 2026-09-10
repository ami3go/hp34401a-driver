"""Robot Framework library for the HP/Agilent/Keysight 34401A DMM."""

from .library import Hp34401ALibrary
from .version import __version__

__all__ = ["Hp34401ALibrary", "__version__"]
