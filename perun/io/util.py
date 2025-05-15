"""IO Util."""

import json
from typing import Any, Tuple

import numpy as np

from perun.data_model.data import Stats
from perun.data_model.measurement_type import Magnitude, MetricMetaData, Number, Unit


def getTFactorMag(value: Number, metric_md: MetricMetaData) -> Tuple[float, Magnitude]:
    """Get transformation factor and magnitude to improve string formating.

    Parameters
    ----------
    value : Number
        Reference value
    metric_md : MetricMetaData
        Value description

    Returns
    -------
    Tuple[float, Magnitude]
        Scaling factor and Magnitude Enum
    """
    if (
        metric_md.unit == Unit.WATT
        or metric_md.unit == Unit.JOULE
        or metric_md.unit == Unit.BYTE
    ):
        transformFactor = 1
        for mag in reversed(Magnitude):
            if value > mag.value:
                transformFactor = mag.value
                break

        newMag = Magnitude(metric_md.mag.value * transformFactor)
        return transformFactor, newMag

    elif metric_md.unit == Unit.PERCENT:
        return 1.0, metric_md.mag
    elif metric_md.unit == Unit.SECOND:
        return 1.0, Magnitude.ONE
    else:
        return 1.0, metric_md.mag


def value2ValueUnitStr(value: Number, metric_md: MetricMetaData) -> str:
    """Return a printable representation as [Value:.3f][mag][unit] (e.g. 3.05mV) of the value based on its metric metadata.

    Parameters
    ----------
    value : Number
        Value to apply formating to.
    metric_md : MetricMetaData
        Value metadata.

    Returns
    -------
    str
        String represenation
    """
    tfactor, new_mag = getTFactorMag(value, metric_md)
    return f"{value / tfactor:.3f} {new_mag.symbol}{metric_md.unit.value}"


def value2MeanStdStr(stats: Stats) -> str:
    """Return a printable representation as [Value:.3f]±[std:.3f][mag][unit] (e.g. 3.05±0.1mV) of the value based on its metric metadata.

    Parameters
    ----------
    stats : Stats obj
        Stats to apply formating to.
    metric_md : MetricMetaData
        Value metadata.

    Returns
    -------
    str
        String represenation
    """
    tfactor, new_mag = getTFactorMag(stats.mean, stats.metric_md)
    return f"{stats.mean / tfactor:.2f} ± {stats.std / tfactor:.2f} {new_mag.symbol}{stats.metric_md.unit.value}"


class NumpyEncoder(json.JSONEncoder):
    """Json Numpy object encoder."""

    def default(self, obj: Any) -> Any:
        """
        Encode an object to a JSON-serializable format, handling NumPy types.

        Parameters
        ----------
        obj : Any
            The object to encode.

        Returns
        -------
        Any
            The JSON-serializable representation of the input object.

        Raises
        ------
        TypeError
            If the object cannot be encoded to a supported format.

        Notes
        -----
        This method specifically handles NumPy integer, floating, ndarray, and dtype objects,
        converting them to standard Python types or string representations. For other types,
        the superclass's default method is called.
        """
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.dtype):
            return str(obj)
        else:
            return super(NumpyEncoder, self).default(obj)
