import configparser
import json
import subprocess
from pathlib import Path

import pytest

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
    print(processorOut)
    parser = configparser.ConfigParser(allow_no_value=True)
    parser.read_string(processorOut)
    assert parser.get("monitor", "sampling_rate") == "2"
    assert parser.get("debug", "log_lvl") == "INFO"
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
    print(processorOut)
    parser = configparser.ConfigParser(allow_no_value=True)
    parser.read_string(processorOut)

    assert parser.get("debug", "log_lvl") == "WARNING"
    assert parser.get("monitor", "sampling_rate") == "1"
    assert parser != defaultConfig


def test_metadata_command(perun: Perun):
    processorOut = subprocess.run(
        ["perun", "metadata"], capture_output=True, text=True, timeout=10
    ).stdout
    metadataJson = json.loads(processorOut)
    for host in perun.host_rank.keys():
        assert host in metadataJson


def test_monitor_command(tmp_path: Path):
    # Test Monitor
    testFilePath = tmp_path / "idle.py"
    with open(testFilePath, "w+") as testFile:
        testFile.write("import time\n\ntime.sleep(10)")

    resultsPath = tmp_path / "results"

    subprocess.run(
        f"perun monitor --data_out {resultsPath} {testFilePath}".split(" "), timeout=20
    )

    # Expected files, hdf5 file and a text file with a date
    # Are the files in the correct folder
    resultFiles = list(resultsPath.iterdir())
    assert len(resultFiles) == 2
    assert resultsPath / "idle.hdf5" in resultFiles
    assert (resultsPath / "idle.hdf5").is_file()

    resultFiles.remove(resultsPath / "idle.hdf5")
    textFile = resultFiles.pop()
    assert textFile.is_file()
    assert textFile.suffix == ".txt"


@pytest.mark.parametrize(
    "format,suffix", [("json", "json"), ("csv", "csv"), ("pickle", "pkl")]
)
def test_export_command(format: str, suffix: str, tmp_path: Path):
    testFilePath = tmp_path / "idle.py"
    with open(testFilePath, "w+") as testFile:
        testFile.write("import time\n\ntime.sleep(10)")

    resultsPath = tmp_path / "results"
    subprocess.run(
        f"perun monitor --data_out {resultsPath} {testFilePath}".split(" "), timeout=20
    )

    # Expected files, hdf5 file and a text file, and a csv file
    # Are the files in the correct folder
    resultFiles = list(resultsPath.iterdir())
    assert len(resultFiles) == 2
    assert resultsPath / "idle.hdf5" in resultFiles

    resultFiles.remove(resultsPath / "idle.hdf5")
    textFile = resultFiles.pop()
    assert textFile.is_file()
    assert textFile.suffix == ".txt"

    # Test export
    subprocess.run(
        f"perun export {resultsPath / 'idle.hdf5'} {format}".split(" "), timeout=10
    )
    resultFiles = list(resultsPath.iterdir())
    assert len(resultFiles) == 3
    assert resultsPath / "idle.hdf5" in resultFiles
    assert textFile in resultFiles

    resultFiles.remove(resultsPath / "idle.hdf5")
    resultFiles.remove(textFile)

    exportedFile = resultFiles.pop()
    assert exportedFile.is_file()
    assert exportedFile.suffix == f".{suffix}"
