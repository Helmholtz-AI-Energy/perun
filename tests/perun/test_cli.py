import os
from click.testing import CliRunner, Result

import perun
from perun.cli import cli
from perun.configuration import _default_config


def test_cli():
    runner = CliRunner()
    output: Result = runner.invoke(cli, ["--version"])
    assert output.output.strip() == f"cli, version {perun.__version__}"


def test_showconf():
    from configparser import ConfigParser

    # Test default option on the default filesystem
    runner = CliRunner()
    output: Result = runner.invoke(cli, ["showconf", "--default"])
    config = ConfigParser()
    config.read_string(output.output)

    for section in _default_config.keys():
        for option, value in _default_config[section].items():
            assert str(value) == config.get(section, option)

    # Test local config file
    with runner.isolated_filesystem():
        with open(".perun.ini", "w") as localConfig:
            localConfig.write("[report]\npue=0.1")
            localConfig.close()

        # Test default is still correct
        output: Result = runner.invoke(cli, ["showconf", "--default"])
        config = ConfigParser()
        config.read_string(output.output)

        for section in _default_config.keys():
            for option, value in _default_config[section].items():
                assert str(value) == config.get(section, option)

        # Test configuration did change
        output: Result = runner.invoke(cli, ["showconf"])
        config = ConfigParser()
        config.read_string(output.output)

        assert config.getfloat("report", "pue") != _default_config["report"]["pue"]
        assert config.getfloat("report", "pue") == 0.1

    # Test cmdline
    output: Result = runner.invoke(cli, ["--pue", "0.1", "showconf", "--default"])
    config = ConfigParser()
    config.read_string(output.output)

    for section in _default_config.keys():
        for option, value in _default_config[section].items():
            assert str(value) == config.get(section, option)

    # Test configuration did change
    output: Result = runner.invoke(cli, ["--pue", "0.1", "showconf"])
    config = ConfigParser()
    config.read_string(output.output)

    assert config.getfloat("report", "pue") != _default_config["report"]["pue"]
    assert config.getfloat("report", "pue") == 0.1

    # # Test env variables
    # output: Result = runner.invoke(cli, ["showconf", "--default"], env={"PERUN_PUE": "0.1"})
    # config = ConfigParser()
    # config.read_string(output.output)
    #
    # for section in _default_config.keys():
    #     for option, value in _default_config[section].items():
    #         assert str(value) == config.get(section, option)
    #
    # # Test configuration did change
    # output: Result = runner.invoke(cli, ["showconf"], env={"PERUN_PUE": "0.1"})
    # config = ConfigParser()
    # config.read_string(output.output)
    #
    # assert config.getfloat("report", "pue") != _default_config["report"]["pue"]
    # assert config.getfloat("report", "pue") == 0.1
