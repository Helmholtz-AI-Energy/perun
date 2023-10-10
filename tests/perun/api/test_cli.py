import subprocess

from perun.api.cli import _get_arg_parser
from perun.perun import Perun
from perun.util import printableSensorConfiguration


def test_no_subcommand():
    processOut = subprocess.run(["perun"], capture_output=True, text=True, timeout=10)
    expectedResult = _get_arg_parser().format_help()
    assert processOut.stdout == expectedResult


def test_sensors_command(perun: Perun):
    processOut = subprocess.run(
        ["perun", "sensors"], capture_output=True, text=True, timeout=10
    ).stdout.rstrip()
    expectedResult = printableSensorConfiguration(
        perun.sensors_config, perun.host_rank
    ).rstrip()
    assert processOut == expectedResult


def test_showconf_command(perun: Perun):
    processorOut = subprocess.run(
        ["perun", "showconf"], capture_output=True, text=True
    ).stdout
    print(processorOut)
