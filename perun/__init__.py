"""perun module."""

# isort: split

from perun.api.decorator import monitor, perun, register_callback
from perun.version import __version__

__all__ = ["monitor", "register_callback", "perun", "__version__"]
