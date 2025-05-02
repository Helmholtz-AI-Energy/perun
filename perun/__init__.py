"""perun module."""

# flake8: noqa
__version__ = "0.8.10"

# isort: split

from perun.api.decorator import monitor, perun, register_callback

__all__ = ["monitor", "register_callback", "perun"]
