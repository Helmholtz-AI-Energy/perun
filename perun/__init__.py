"""perun module."""
# flake8: noqa
__version__ = "0.1.1"
from perun.configuration import config
from perun.logging import init_logging

log = init_logging(config.get("debug", "log_lvl"))

import os

os.environ["IBV_FORK_SAFE"] = "1"
os.environ["RDMAV_FORK_SAFE"] = "1"

from perun.comm import Comm

COMM_WORLD = Comm()
