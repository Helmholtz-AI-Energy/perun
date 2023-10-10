# noqa
import pytest

from perun import config
from perun.perun import Perun


@pytest.fixture(scope="package")
def perun():
    return Perun(config)
