"""Configuration module."""

# gCO2eq/kWh - source: https://ourworldindata.org/grapher/carbon-intensity-electricity Global Average
# Currency/kWh (Euro) - source: https://www.stromauskunft.de/strompreise/ 03.05.2023
import configparser
import os
from pathlib import Path
from typing import Any, Mapping

_default_config: Mapping[str, Mapping[str, Any]] = {
    "post-processing": {
        "power_overhead": 0,  # Watt
        "pue": 1.0,  # Global Average Power Usage Effectiveness (2022 or something)
        "emissions_factor": 417.80,  # gCO2eq/kWh
        "price_factor": 0.3251,  # Currency/kWh
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
    },
    "benchmarking.units": {"joule": "k", "second": "", "percent": "", "power": ""},
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
    pathStr: str,
) -> None:
    """Read INI config file and save in global configuration objects.

    Parameters
    ----------
    pathStr : str
        Path to configuration file.
    """
    configPath: Path = Path(pathStr)
    if configPath.exists() and configPath.is_file():
        config.read(configPath)


def save_to_config(key: str, value: Any):
    """Save key and value to configuration.

    Parameters
    ----------
    key : str
        Option name
    value : Any
        Option value
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
