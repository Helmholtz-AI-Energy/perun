from configparser import ConfigParser

from click.testing import CliRunner, Result

import perun
from perun.api.cli import cli
from perun.configuration import _default_config


def test_cli():
    runner = CliRunner()
    output: Result = runner.invoke(cli, ["--version"])
    assert output.output.strip() == f"cli, version {perun.__version__}"


def test_cli_showconf():
    # Test default option on the default filesystem
    runner = CliRunner()
    output: Result = runner.invoke(cli, ["showconf", "--default"])
    print(output.output)
    config = ConfigParser(allow_no_value=True)
    config.read_string(
        output.output,
    )

    for section in _default_config.keys():
        for option, value in _default_config[section].items():
            if value is not None:
                assert str(value) == config.get(section, option)
            else:
                assert value == config.get(section, option)

    # Test local config file
    with runner.isolated_filesystem():
        with open(".perun.ini", "w") as localConfig:
            localConfig.write("[post-processing]\npue=0.1")
            localConfig.close()

        # Test default is still correct
        output: Result = runner.invoke(cli, ["showconf", "--default"])
        config = ConfigParser(allow_no_value=True)
        config.read_string(output.output)

        for section in _default_config.keys():
            for option, value in _default_config[section].items():
                if value is not None:
                    assert str(value) == config.get(section, option)
                else:
                    assert value == config.get(section, option)

        # Test configuration did change
        output: Result = runner.invoke(cli, ["showconf"])
        config = ConfigParser(allow_no_value=True)
        config.read_string(output.output)

        assert (
            config.getfloat("post-processing", "pue")
            != _default_config["post-processing"]["pue"]
        )
        assert config.getfloat("post-processing", "pue") == 0.1

    # # Test env variables
    # monkeypatch.setenv("PERUN_PUE", "0.1")
    # runner = CliRunner()
    # output: Result = runner.invoke(cli, ["showconf", "--default"])
    # config = ConfigParser()
    # config.read_string(output.output)
    #
    # for section in _default_config.keys():
    #     for option, value in _default_config[section].items():
    #         assert str(value) == config.get(section, option)
    #
    # # Test configuration did change
    # with monkeypatch.context() as m:
    #     m.setenv("PERUN_PUE", "0.1")
    #     output: Result = runner.invoke(cli, ["showconf"])
    #     config = ConfigParser()
    #     config.read_string(output.output)
    #
    #     assert config.getfloat("post-processing", "pue") != _default_config["report"]["pue"]
    #     assert config.getfloat("post-processing", "pue") == 0.1
