"""Util module."""
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Tuple, Union

import numpy as np

from perun import config
from perun.data_model.measurement_type import Magnitude, MetricMetaData, Unit


def getRunName(app: Union[Path, Callable]) -> str:
    """Return application name based on available info.

    Args:
        app (Union[Path, Callable]): The path or function that is being monitored.

    Returns:
        str: Application name.
    """
    if config.get("output", "app_name"):
        return config.get("output", "app_name")
    elif "SBATCH_JOB_NAME" in os.environ:
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
    if config.get("output", "run_id"):
        return config.get("output", "run_id")
    elif "SLURM_JOB_ID" in os.environ:
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
