"""perun module."""
# flake8: noqa
__version__ = "0.1.0"

import os
from dotenv import load_dotenv
from perun.logging import init_logging

# SETUP ENV
load_dotenv()
os.environ["IBV_FORK_SAFE"] = "1"
os.environ["RDMAV_FORK_SAFE"] = "1"
log = init_logging(os.environ["LOG_LVL"])

from perun.perun import perunSubprocess, getDeviceConfiguration
from perun.storage import LocalStorage, ExperimentStorage
from perun.backend import backends, Device

__all__ = [
    "perunSubprocess",
    "getDeviceConfiguration",
    "LocalStorage",
    "ExperimentStorage",
    "backends",
    "Device",
    "log",
]
