"""perun module."""
# flake8: noqa
__version__ = "0.1.0-beta.7"

import os
from dotenv import load_dotenv
from perun.logging import init_logging

# SETUP ENV
load_dotenv()
os.environ["IBV_FORK_SAFE"] = "1"
os.environ["RDMAV_FORK_SAFE"] = "1"
log_lvl = os.environ["LOG_LVL"] if "LOG_LVL" in os.environ else "INFO"
log = init_logging(log_lvl)

from perun.perun import perunSubprocess, getDeviceConfiguration, monitor, postprocessing
from perun.storage import LocalStorage, ExperimentStorage
from perun.backend import backends, Device
from perun.report import report


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
