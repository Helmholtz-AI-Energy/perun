# noqa
import configparser

import pytest

from perun.configuration import _default_config
from perun.perun import Perun


@pytest.fixture(scope="package")
def defaultConfig():
    defaultConfig = configparser.ConfigParser(allow_no_value=True)
    defaultConfig.read_dict(_default_config)
    return defaultConfig


@pytest.fixture(scope="package")
def perun(defaultConfig):
    return Perun(defaultConfig)
