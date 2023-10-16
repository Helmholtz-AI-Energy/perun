"""perun module."""
# flake8: noqa
__version__ = "0.5.0-rc.1"
from perun.configuration import config
from perun.logging import init_logging

log = init_logging(config.get("debug", "log_lvl"))

from perun.api.decorator import monitor
