# noqa
import configparser

import pytest

from perun.configuration import _default_config
from perun.core import Perun
from perun.backend.backend import Backend
from perun.backend.nvml import NVMLBackend
from perun.backend.powercap_rapl import PowercapRAPLBackend
from perun.backend.psutil import PSUTILBackend
from perun.backend.rocmsmi import ROCMBackend

@pytest.fixture()
def defaultConfig():
    defaultConfig = configparser.ConfigParser(allow_no_value=True)
    defaultConfig.read_dict(_default_config)
    return defaultConfig


@pytest.fixture(scope="function")
def perun(defaultConfig):
    return Perun(defaultConfig)


@pytest.fixture(scope="function")
def setup_cleanup():
    # Setup
    Perun._instances = {}
    NVMLBackend._instances = {}
    PowercapRAPLBackend._instances = {}
    PSUTILBackend._instances = {}
    ROCMBackend._instances = {}

    yield
    # Cleanup

    Perun._instances = {}
    NVMLBackend._instances = {}
    PowercapRAPLBackend._instances = {}
    PSUTILBackend._instances = {}
    ROCMBackend._instances = {}
