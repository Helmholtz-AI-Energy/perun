from datetime import timedelta
from typing import Tuple

import numpy as np

from perun.data_model.measurement_type import Magnitude, MetricMetaData, Unit


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
