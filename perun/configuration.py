"""Configuration module."""
# gCO2eq/kWh - source: https://ourworldindata.org/grapher/carbon-intensity-electricity Global Average
# cent/kWh (Euro) - source: https://www.stromauskunft.de/strompreise/ 03.05.2023
import configparser
import os
from pathlib import Path
from typing import Any, Mapping, Optional, Union

import click

_default_config: Mapping[str, Mapping[str, Any]] = {
    "post-processing": {
        "pue": 1.58,
        "emissions_factor": 417.80,  # gCO2eq/kWh
        "price_factor": 32.51,  # Cent/kWh
        "price_unit": "€",
    },
    "monitor": {
        "sampling_rate": 1,
    },
    "output": {
        "app_name": None,
        "run_id": None,
        "format": "text",
        "data_out": "./perun_results",
    },
    "benchmarking": {
        "rounds": 1,
        "warmup_rounds": 0,
        # "bench_metrics": ["ENERGY", "RUNTIME"],
    },
    "debug": {"log_lvl": "WARNING"},
    # "horeka": {"enabled": False, "url": "", "token": "", "org": ""},
}

config: configparser.ConfigParser = configparser.ConfigParser(allow_no_value=True)
config.read_dict(_default_config)

globalConfigPath = Path.home() / ".config/perun.ini"
if globalConfigPath.exists() and globalConfigPath.is_file():
    config.read(globalConfigPath)

localConfigPath = Path.cwd() / ".perun.ini"
if globalConfigPath.exists() and globalConfigPath.is_file():
    config.read(globalConfigPath)


def read_custom_config(
    ctx: Optional[click.Context],
    param: Optional[Union[click.Option, click.Parameter]],
    pathStr: str,
) -> None:
    """Read an INI configuration file and overrides the values from the default and global configuration.

    :param ctx: Command line context object (ignore)
    :type ctx: Optional[click.Context]
    :param param: Click CLI object (ignore)
    :type param: Optional[Union[click.Option, click.Parameter]]
    :param pathStr: String to configuration file (don't ignore)
    :type pathStr: str
    """
    configPath: Path = Path(pathStr)
    if configPath.exists() and configPath.is_file():
        config.read(configPath)


def save_to_config_callback(
    ctx: click.Context, param: Union[click.Option, click.Parameter], value: Any
):
    """Override configuration with click cli options.

    :param ctx: Click context (ignore)
    :type ctx: click.Context
    :param param: Click parameters/options
    :type param: Union[click.Option, click.Parameter]
    :param value: New configuration value
    :type value: Any
    """
    if value and isinstance(param, click.Option):
        key: Optional[str] = param.name
        if key:
            save_to_config(key, value)


def save_to_config(key: str, value: Any):
    """Override individual configuration values.

    :param key: Option name
    :type key: str
    :param value: Option value
    :type value: Any
    """
    for section in config.sections():
        if config.has_option(section, key):
            config.set(section, key, str(value))


def read_environ():
    """Read perun environmental variables."""
    for section, subconf in _default_config.items():
        for option in subconf.keys():
            envvar = f"PERUN_{option.upper()}"
            if envvar in os.environ:
                config.set(section, option, os.environ[envvar])
