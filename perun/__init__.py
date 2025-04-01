"""perun module."""

# flake8: noqa
__version__ = "0.8.10"
from perun.configuration import config
from perun.logging import init_logging

log = init_logging(config.get("debug", "log_lvl"))

# isort: split

from perun.api.decorator import monitor, perun, register_callback

__all__ = ["monitor", "register_callback", "perun"]
