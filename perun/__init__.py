"""perun module."""

# isort: split

from perun.api.decorator import (
    monitor,
    perun,
    register_callback,
    register_live_callback,
)
from perun.version import __version__

__all__ = [
    "monitor",
    "register_callback",
    "register_live_callback",
    "perun",
    "__version__",
]
