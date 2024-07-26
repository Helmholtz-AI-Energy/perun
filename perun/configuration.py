"""Configuration module."""

# gCO2eq/kWh - source: https://ourworldindata.org/grapher/carbon-intensity-electricity Global Average
# Currency/kWh (Euro) - source: https://www.stromauskunft.de/strompreise/ 03.05.2023
import configparser
import logging
import os
import pprint as pp
from pathlib import Path
from typing import Any, Mapping

from perun.io.io import IOFormat

log = logging.getLogger("perun")

_default_config: Mapping[str, Mapping[str, Any]] = {
    "post-processing": {
        "power_overhead": 0,  # Watt
        "pue": 1.0,  # Global Average Power Usage Effectiveness (2022 or something)
        "emissions_factor": 417.80,  # gCO2eq/kWh
        "price_factor": 0.3251,  # Currency/kWh
        "price_unit": "€",
    },
    "monitor": {
        "sampling_period": 1,
        "include_backends": "",
        "include_sensors": "",
        "exclude_backends": "",
        "exclude_sensors": "",
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
        "metrics": "runtime,energy",
        "region_metrics": "runtime,power",
    },
    "benchmarking.units": {
        "joule": "k",
        "second": "",
        "percent": "",
        "watt": "",
        "byte": "G",
    },
    "debug": {"log_lvl": "WARNING"},
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


def sanitize_config(config) -> configparser.ConfigParser:
    """Sanitize configuration values.

    Parameters
    ----------
    config : configparser.ConfigParser
        Configuration object.

    Returns
    -------
    configparser.ConfigParser
        Sanitized configuration object.
    """
    # Ensure post processing variables are valid
    try:
        power_overhead = config.getfloat("post-processing", "power_overhead")
        if power_overhead < 0:
            log.warning(
                f"Invalid power overhead {power_overhead}. Should be a number higher or equal than 0. Defaulting to 0."
            )
            config.set("post-processing", "power_overhead", "0")
    except ValueError:
        log.warning(
            "Invalid power overhead. Should be a number higher or equal than 0. Defaulting to 0."
        )
        config.set("post-processing", "power_overhead", "0")

    try:
        pue = config.getfloat("post-processing", "pue")
        if pue < 1:
            log.warning(
                f"Invalid PUE {pue}. Should be a number higher or equal than 1. Defaulting to 1."
            )
            config.set("post-processing", "pue", "1.0")
    except ValueError:
        log.warning(
            "Invalid PUE. Should be a number higher or equal than 1. Defaulting to 1."
        )
        config.set("post-processing", "pue", "1.0")

    try:
        emissions_factor = config.getfloat("post-processing", "emissions_factor")
        if emissions_factor < 0:
            log.warning(
                f"Invalid emissions factor {emissions_factor}. Should be a number higher or equal than 0. Defaulting to 417.80 gCO2eq/kWh."
            )
            config.set("post-processing", "emissions_factor", "417.80")
    except ValueError:
        log.warning(
            "Invalid emissions factor. Should be a number higher or equal than 0. Defaulting to 417.80 gCO2eq/kWh."
        )
        config.set("post-processing", "emissions_factor", "417.80")

    try:
        price_factor = config.getfloat("post-processing", "price_factor")
        if price_factor < 0:
            log.warning(
                f"Invalid price factor {price_factor}. Should be a number higher or equal than 0. Defaulting to 0.3251 Currency/kWh."
            )
            config.set("post-processing", "price_factor", "0.3251")
    except ValueError:
        log.warning(
            "Invalid price factor. Should be a number higher or equal than 0. Defaulting to 0.3251 Currency/kWh."
        )
        config.set("post-processing", "price_factor", "0.3251")

    # Ensure that the monitoring options are valid
    try:
        sampling_period = config.getfloat("monitor", "sampling_period")
        if sampling_period < 0.1:
            log.warning(
                f"Invalid sampling period {sampling_period}. Should be a number higher than 0.1 . Defaulting to 1."
            )
            config.set("monitor", "sampling_period", "1")
    except ValueError:
        log.warning(
            "Invalid sampling period. Should be a number higher than 0.1 . Defaulting to 1."
        )
        config.set("monitor", "sampling_period", "1")

    # Ensure only the include or exclude options are set
    include_backends = config.get("monitor", "include_backends")
    include_sensors = config.get("monitor", "include_sensors")
    exclude_backends = config.get("monitor", "exclude_backends")
    exclude_sensors = config.get("monitor", "exclude_sensors")

    if include_backends and exclude_backends:
        log.warning(
            "Both include and exclude backends options are set. Defaulting to exclude only."
        )
        config.set("monitor", "include_backends", "")

    if include_sensors and exclude_sensors:
        log.warning(
            "Both include and exclude sensors options are set. Defaulting to exclude only."
        )
        config.set("monitor", "include_sensors", "")

    # Ensure that the output format is valid
    try:
        format = config.get("output", "format")
        IOFormat(format)
    except ValueError:
        log.warning(
            f"Invalid output format {format}. Defaulting to text. Avilable formats: {pp.pformat([f.value for f in IOFormat])}"
        )
        config.set("output", "format", IOFormat.TEXT.value)

    # Ensure that the rounds and warmup rounds are valid
    try:
        rounds = config.getint("benchmarking", "rounds")
        if rounds < 1:
            log.warning(
                f"Invalid number rounds {rounds}. Should be a number higher than 1. Defaulting to 1."
            )
            config.set("benchmarking", "rounds", "1")
    except ValueError:
        log.warning(
            "Invalid number rounds. Should be a number higher than 1. Defaulting to 1."
        )
        config.set("benchmarking", "rounds", "1")

    try:
        warmup_rounds = config.getint("benchmarking", "warmup_rounds")
        if warmup_rounds < 0:
            log.warning(
                f"Invalid number warmup rounds {warmup_rounds}. Should be a number higher than 0. Defaulting to 0."
            )
            config.set("benchmarking", "warmup_rounds", "0")
    except ValueError:
        log.warning(
            "Invalid number warmup rounds. Should be a number higher than 0. Defaulting to 0."
        )
        config.set("benchmarking", "warmup_rounds", "0")

    # Ensure that the log_lvl is valid
    log_lvl = config.get("debug", "log_lvl")
    if log_lvl not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        log.warning(f"Invalid log level {log_lvl}. Defaulting to WARNING.")
        config.set("debug", "log_lvl", "WARNING")

    return config
