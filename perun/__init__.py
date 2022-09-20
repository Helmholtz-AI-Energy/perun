"""perun module."""
# flake8: noqa
__version__ = "0.1.0-beta.16"
from perun.configuration import config
from perun.logging import init_logging

log = init_logging(config.get("perun", "log_lvl"))

import os

os.environ["IBV_FORK_SAFE"] = "1"
os.environ["RDMAV_FORK_SAFE"] = "1"

from perun.perun import (
    getDeviceConfiguration,
    monitor,
    perunSubprocess,
    postprocessing,
    save_data,
)
from perun.report import report
from perun.storage import ExperimentStorage, LocalStorage

__all__ = [
    "perunSubprocess",
    "getDeviceConfiguration",
    "LocalStorage",
    "ExperimentStorage",
    "log",
    "monitor",
    "report",
    "postprocessing",
    "config",
    "save_data",
]
