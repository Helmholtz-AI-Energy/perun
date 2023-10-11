import configparser
import subprocess
from pathlib import Path

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


def test_showconf_command(defaultConfig: configparser.ConfigParser):
    # 1) Are the outputs the same?
    processorOut = subprocess.run(
        ["perun", "showconf"], capture_output=True, text=True
    ).stdout
    parser = configparser.ConfigParser(allow_no_value=True)
    parser.read_string(processorOut)
    assert parser == defaultConfig


def test_showconf_command_with_cli_args(defaultConfig: configparser.ConfigParser):
    # 2) Are cli arguments correctly set?
    processorOut = subprocess.run(
        ["perun", "--log_lvl", "ERROR", "showconf"], capture_output=True, text=True
    ).stdout
    parser = configparser.ConfigParser(allow_no_value=True)
    parser.read_string(processorOut)
    defaultConfig.set("debug", "log_lvl", "ERROR")
    assert parser == defaultConfig


def test_showconf_command_with_conf_file(
    defaultConfig: configparser.ConfigParser, tmp_path: Path
):
    # 3) Are files read correctly?
    confPath = tmp_path / ".perun.ini"
    defaultConfig.set("monitor", "sampling_rate", "2")
    with open(confPath, "w+") as configFile:
        defaultConfig.write(configFile)

    processorOut = subprocess.run(
        ["perun", "--configuration", str(confPath), "showconf"],
        capture_output=True,
        text=True,
    ).stdout
    parser = configparser.ConfigParser(allow_no_value=True)
    parser.read_string(processorOut)
    assert parser.get("monitor", "sampling_rate") == "2"
    assert parser == defaultConfig


def test_showconf_command_with_default(
    defaultConfig: configparser.ConfigParser, tmp_path: Path
):
    # 4) Does default ignore everything?
    confPath = tmp_path / ".perun.ini"
    defaultConfig.set("monitor", "sampling_rate", "2")
    with open(confPath, "w+") as configFile:
        defaultConfig.write(configFile)

    processorOut = subprocess.run(
        ["perun", "--log_lvl", "INFO", "--configuration", str(confPath), "showconf"],
        capture_output=True,
        text=True,
    ).stdout
    parser = configparser.ConfigParser(allow_no_value=True)
    parser.read_string(processorOut)
    assert parser.get("debug", "log_lvl") == "INFO"
    assert parser.get("monitor", "sampling_rate") == "2"
    assert parser != defaultConfig

    defaultConfig.set("monitor", "sampling_rate", "1")
    processorOut = subprocess.run(
        [
            "perun",
            "--log_lvl",
            "INFO",
            "--configuration",
            str(confPath),
            "showconf",
            "--default",
        ],
        capture_output=True,
        text=True,
    ).stdout
    parser = configparser.ConfigParser(allow_no_value=True)
    parser.read_string(processorOut)

    assert parser.get("debug", "log_lvl") == "WARNING"
    assert parser.get("monitor", "sampling_rate") == "1"
    assert parser != defaultConfig
