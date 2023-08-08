"""perun module."""
# flake8: noqa
__version__ = "0.3.2"
from perun.configuration import config
from perun.logging import init_logging
from perun.api.decorator import monitor

log = init_logging(config.get("debug", "log_lvl"))
