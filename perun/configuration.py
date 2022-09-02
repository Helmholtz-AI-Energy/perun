"""Configuration module."""

# Watt/GB (from : https://www.crucial.com/support/articles-faq-memory/how-much-power-does-memory-use)
# kgCO2eq/kWh - source https://www.nowtricity.com/country/germany/
# cent/kWh (Euro) - source: https://www.stromauskunft.de/strompreise/ Baden-Württemberg lokare anbieter

import configparser
from pathlib import Path
from typing import Any, Mapping, Union

import click

_default_config: Mapping[str, Mapping[str, Any]] = {
    "report": {
        "format": "txt",
        "pue": 1.58,
        "emissions-factor": 0.355,
        "price-factor": 41.59,
    },
    "devices": {
        "ram2watt": 3 / 8.0,
    },
    "monitor": {"frequency": 1, "data_out": "./results"},
    "perun": {"log_lvl": "WARN"},
    "horeka": {"enabled": False, "url": "", "token": "", "org": ""},
}

config: configparser.ConfigParser = configparser.ConfigParser()
config.read_dict(_default_config)

globalConfigPath = Path.home() / ".config/perun.ini"
if globalConfigPath.exists() and globalConfigPath.is_file():
    config.read(globalConfigPath)


def read_custom_config(
    ctx: click.Context, param: Union[click.Option, click.Parameter], pathStr: str
) -> None:
    """
    Read an INI configuration file and overrides the values from the default and global configuration.

    Args:
        ctx (click.Context): Commandline context object (irrelevant)
        param (Union[click.Option, click.Parameter]): Click cli object (irrelevant)
        pathStr (str): String to configuration file
    """
    configPath: Path = Path(pathStr)
    if configPath.exists() and configPath.is_file():
        config.read(configPath)


def save_to_config_callback(
    ctx: click.Context, param: Union[click.Option, click.Parameter], value: Any
):
    """
    Override configuration with click cli options.

    Args:
        ctx (click.Context): Click context
        param (Union[click.Option, click.Parameter]): Click option/param object
        value (Any): New configuration value
    """
    if value and isinstance(param, click.Option):
        key: str = param.name
        save_to_config(key, value)


def save_to_config(key: str, value: Any):
    """
    Override indivial configuration values.

    Args:
        key (str): Option name
        value (Any): New option value
    """
    for section in config.sections():
        if config.has_option(section, key):
            config.set(section, key, str(value))
