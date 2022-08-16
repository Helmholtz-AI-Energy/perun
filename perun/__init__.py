"""perun module."""
# flake8: noqa
__version__ = "0.1.0-beta.7"

import os

from dotenv import load_dotenv

from perun.backend import Device, backends
from perun.logging import init_logging
from perun.perun import getDeviceConfiguration, monitor, perunSubprocess, postprocessing
from perun.report import report
from perun.storage import ExperimentStorage, LocalStorage

# SETUP ENV
load_dotenv()
os.environ["IBV_FORK_SAFE"] = "1"
os.environ["RDMAV_FORK_SAFE"] = "1"
log_lvl = os.environ["LOG_LVL"] if "LOG_LVL" in os.environ else "INFO"
log = init_logging(log_lvl)


__all__ = [
    "perunSubprocess",
    "getDeviceConfiguration",
    "LocalStorage",
    "ExperimentStorage",
    "backends",
    "Device",
    "log",
    "monitor",
    "report",
]
