"""Configuration module."""
# kgCO2eq/kWh - source https://www.nowtricity.com/country/germany/
# cent/kWh (Euro) - source: https://www.stromauskunft.de/strompreise/ Baden-Württemberg lokare anbieter

import configparser
from pathlib import Path
from typing import Any, Mapping, Optional, Union

import click

_default_config: Mapping[str, Mapping[str, Any]] = {
    "post-processing": {
        "pue": 1.58,
        "emissions_factor": 0.262,  # gCO2eq/kWh
        "price_factor": 34.60,  # Cent/kWh
    },
    "monitor": {
        "sampling_rate": 1,
    },
    "output": {
        "app_name": None,
        "run_id": None,
        "format": "text",
        "data_out": "./perun_results",
        "depth": None,
        "raw": False,
    },
    "benchmarking": {
        "bench_enable": False,
        "bench_rounds": 10,
        "bench_warmup_rounds": 1,
        # "bench_metrics": ["ENERGY", "RUNTIME"],
    },
    "debug": {"log_lvl": "ERROR"},
    # "horeka": {"enabled": False, "url": "", "token": "", "org": ""},
}

config: configparser.ConfigParser = configparser.ConfigParser(allow_no_value=True)
config.read_dict(_default_config)

globalConfigPath = Path.home() / ".config/perun.ini"
if globalConfigPath.exists() and globalConfigPath.is_file():
    config.read(globalConfigPath)


def read_custom_config(
    ctx: Optional[click.Context],
    param: Optional[Union[click.Option, click.Parameter]],
    pathStr: str,
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
        key: Optional[str] = param.name
        if key:
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
