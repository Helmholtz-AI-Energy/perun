# noqa
import configparser

import pytest

from perun.configuration import _default_config
from perun.core import Perun


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

    yield
    # Cleanup

    Perun._instances = {}
