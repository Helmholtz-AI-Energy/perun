"""Util module."""
import os
import platform
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, Set, Tuple, Union

import numpy as np

from perun import config, log
from perun.data_model.measurement_type import Magnitude, MetricMetaData, Unit


def getRunName(app: Union[Path, Callable]) -> str:
    """Return application name based on available info.

    Args:
        app (Union[Path, Callable]): The path or function that is being monitored.

    Returns:
        str: Application name.
    """
    app_name = config.get("output", "app_name")

    if app_name and app_name != "SLURM":
        return config.get("output", "app_name")
    elif app_name and "SBATCH_JOB_NAME" in os.environ and app_name == "SLURM":
        return os.environ["SBATCH_JOB_NAME"]
    elif isinstance(app, Path):
        return app.stem
    else:
        return app.__name__


def getRunId(startime: datetime) -> str:
    """Get run id from available info.

    Args:
        startime (datetime): Time when application was started.

    Returns:
        str: String id.
    """
    run_id = config.get("output", "run_id")
    if run_id and run_id != "SLURM":
        return config.get("output", "run_id")
    elif (
        run_id
        and "SLURM_JOB_ID" in os.environ
        and config.get("output", "run_id") == "SLURM"
    ):
        return os.environ["SLURM_JOB_ID"]
    else:
        return startime.isoformat()


def value2str(
    value: np.number, metric_md: MetricMetaData
) -> Tuple[str, float, Magnitude]:
    """Return a printable representation of the value based on its metric metadata. A printable value should not have more than 3 digits after before the decimal comma/dot.

    Args:
        value (np.number): Value to format.
        metric_md (MetricMetaData): Value metadata.

    Returns:
        Tuple[str, float, Magnitude]: Formated value, transformation factor used, and the new magnitude prefix.
    """
    if metric_md.unit == Unit.WATT or metric_md.unit == Unit.JOULE:
        transformFactor = 1
        for mag in reversed(Magnitude):
            if value > mag.value:
                transformFactor = mag.value
                break

        newValue = value / transformFactor
        newMag = Magnitude(metric_md.mag.value * transformFactor)
        return f"{newValue:.3f}", transformFactor, newMag

    elif metric_md.unit == Unit.PERCENT:
        return f"{value:.3f}", 1.0, metric_md.mag
    elif metric_md.unit == Unit.SECOND:
        return str(timedelta(seconds=float(value))), 1.0, Magnitude.ONE
    elif metric_md.unit == Unit.BYTE:
        transformFactor = 1
        newMag = Magnitude.ONE
        for magFactor, m in zip(
            [1024**3, 1024**2, 1024**1],
            [Magnitude.GIGA, Magnitude.MEGA, Magnitude.KILO],
        ):
            if value > magFactor:
                transformFactor = magFactor
                newMag = m
                break

        newValue = value / transformFactor
        return f"{newValue:.3f}", transformFactor, newMag
    else:
        return f"{value:.3f}", 1.0, metric_md.mag


def getHostMetadata(backendConfig: Dict[str, Set[str]]) -> Dict[str, Any]:
    """Return dictionary with the full system metadata based on the provided backend configuration.

    :param backendConfig: Sensor backend configuration to include in the metadata object.
    :type backendConfig: Dict[str, Set[str]]
    :return: Dictionary with system metadata
    :rtype: Dict[str, Any]
    """
    from perun.backend import backends

    metadata = {}
    for name, method in platform.__dict__.items():
        if callable(method):
            try:
                metadata[name] = method()
            except Exception as e:
                log.warn(f"platform method {name} did not work")
                log.warn(e)

    metadata["backends"] = {}
    for backend in backends:
        if backend.name in backendConfig:
            metadata["backends"][backend.name] = {}
            sensors = backend.getSensors(backendConfig[backend.name])
            for sensor in sensors:
                metadata["backends"][backend.name][sensor.id] = sensor.metadata

    return metadata
