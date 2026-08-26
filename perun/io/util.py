"""IO Util."""

import json
from collections.abc import Sequence
from typing import Any, Tuple, cast

import numpy as np
import pandas as pd

from perun.data_model.data import Stats
from perun.data_model.measurement_type import Magnitude, MetricMetaData, Number, Unit


def dataframe_to_markdown(df: pd.DataFrame, stralign: str = "right") -> str:
    """Render a DataFrame as a GitHub-flavoured markdown pipe table.

    This is a dependency-free replacement for ``DataFrame.to_markdown`` (which
    requires the optional ``tabulate`` package). It reproduces the previous
    output style used in perun reports: a header row, a separator row, and one
    row per record, with cells aligned according to ``stralign``.

    Parameters
    ----------
    df : pandas.DataFrame
        Table to render. The index is not included.
    stralign : str, optional
        Column alignment, one of ``"right"``, ``"left"`` or ``"center"``.
        Defaults to ``"right"`` to match the historical report format.

    Returns
    -------
    str
        The markdown table as a string (no trailing newline).
    """
    columns = [str(c) for c in df.columns]

    def _fmt(value: Any) -> str:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return ""
        return str(value)

    rows: list[list[str]] = [
        [_fmt(v) for v in record] for record in df.to_numpy().tolist()
    ]

    # Column width is the widest cell/header, matching the GitHub-flavoured
    # markdown output of tabulate/pandas.to_markdown.
    widths = [len(col) for col in columns]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def _align(text: str, width: int) -> str:
        if stralign == "left":
            return text.ljust(width)
        if stralign == "center":
            return text.center(width)
        return text.rjust(width)

    def _render_row(cells: Sequence[str]) -> str:
        return (
            "| " + " | ".join(_align(c, widths[i]) for i, c in enumerate(cells)) + " |"
        )

    # Separator matches tabulate's "github" style: the colon marking alignment
    # replaces the outermost dash, with no surrounding spaces, and the cell
    # spans width + 2 characters (the padding around each column).
    def _sep(width: int) -> str:
        length = width + 2
        if stralign == "center":
            return ":" + "-" * max(length - 2, 1) + ":"
        if stralign == "left":
            return ":" + "-" * max(length - 1, 1)
        return "-" * max(length - 1, 1) + ":"

    header = _render_row(columns)
    separator = "|" + "|".join(_sep(w) for w in widths) + "|"
    body = "\n".join(_render_row(row) for row in rows)
    return (
        "\n".join([header, separator, body]) if body else "\n".join([header, separator])
    )


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


# Maps a "device" metric to the sensor unit and device types whose raw
# time-series should be used to compute its min / max / avg. RUNTIME and the
# cumulative ENERGY metrics are intentionally absent: a per-sample min/max is
# not meaningful for them.
_RAW_METRIC_SOURCES: dict[Any, tuple[Any, tuple[Any, ...]]] = {}


def _init_raw_metric_sources() -> dict[Any, tuple[Any, tuple[Any, ...]]]:
    """Build (and cache) the metric -> (unit, device types) lookup table.

    Done lazily to avoid importing the data model enums at module import time
    in a way that could create import cycles.
    """
    global _RAW_METRIC_SOURCES
    if _RAW_METRIC_SOURCES:
        return _RAW_METRIC_SOURCES

    from perun.data_model.data import MetricType
    from perun.data_model.sensor import DeviceType

    _RAW_METRIC_SOURCES = {
        # Power: derived from WATT/JOULE sensors of the matching device type.
        MetricType.POWER: (
            Unit.WATT,
            (DeviceType.CPU, DeviceType.GPU, DeviceType.RAM, DeviceType.OTHER),
        ),
        MetricType.CPU_POWER: (Unit.WATT, (DeviceType.CPU,)),
        MetricType.GPU_POWER: (Unit.WATT, (DeviceType.GPU,)),
        MetricType.DRAM_POWER: (Unit.WATT, (DeviceType.RAM,)),
        MetricType.OTHER_POWER: (Unit.WATT, (DeviceType.OTHER,)),
        # Utilisation: PERCENT sensors.
        MetricType.CPU_UTIL: (Unit.PERCENT, (DeviceType.CPU,)),
        MetricType.GPU_UTIL: (Unit.PERCENT, (DeviceType.GPU,)),
        MetricType.OTHER_UTIL: (Unit.PERCENT, (DeviceType.OTHER,)),
        # Memory: BYTE sensors.
        MetricType.GPU_MEM: (Unit.BYTE, (DeviceType.GPU,)),
        MetricType.DRAM_MEM: (Unit.BYTE, (DeviceType.RAM,)),
        MetricType.OTHER_MEM: (Unit.BYTE, (DeviceType.OTHER,)),
    }
    return _RAW_METRIC_SOURCES


def _sensor_power_series(raw_data: Any) -> np.ndarray:
    """Return the per-sample power series (in Watts) for an energy/power sensor.

    Works on a copy so the sensor's ``raw_data`` is never mutated. If the
    sensor already stores a processed power series (unit WATT) it is returned
    scaled to its magnitude; if it stores raw energy (unit JOULE) the power
    series is derived with the same logic used during processing.
    """
    import copy as _copy

    from perun.data_model.data import RawData

    # processEnergyData mutates its argument, so operate on a copy.
    rd: RawData = _copy.deepcopy(raw_data)
    if rd.v_md.unit == Unit.WATT:
        mag_factor = rd.v_md.mag.value / Magnitude.ONE.value
        return cast(np.ndarray, rd.values.astype("float32") * mag_factor)

    # JOULE -> derive power via the shared processing routine.
    from perun.processing import processEnergyData

    _, _ = processEnergyData(rd)
    # processEnergyData rewrites rd.values into the power series (Watts).
    return rd.values.astype("float32")


def raw_metric_stats(
    node: Any, metric_type: Any
) -> Tuple[Number, Number, Number, MetricMetaData] | None:
    """Compute (min, mean, max, metadata) for a metric from raw sensor data.

    The statistics are taken directly from the underlying sensor time-series
    found beneath ``node`` (a host, device-group or run node), which is exactly
    the raw data recorded during monitoring. Returns ``None`` when the metric
    has no per-sample series (e.g. RUNTIME, ENERGY) or no matching sensor data
    is available.

    Parameters
    ----------
    node : DataNode
        Any node in the tree; its sensor descendants are searched.
    metric_type : MetricType
        The metric whose raw statistics are requested.

    Returns
    -------
    tuple | None
        ``(min, mean, max, metric_md)`` in base magnitude, or ``None``.
    """
    from perun.data_model.data import NodeType

    sources = _init_raw_metric_sources()
    if metric_type not in sources:
        return None

    unit, device_types = sources[metric_type]

    series: list[np.ndarray] = []
    result_md: MetricMetaData | None = None

    def _collect(n: Any) -> None:
        nonlocal result_md
        if n.type == NodeType.SENSOR and n.raw_data is not None:
            if n.deviceType not in device_types:
                return
            rd = n.raw_data
            if unit == Unit.WATT:
                if rd.v_md.unit not in (Unit.WATT, Unit.JOULE):
                    return
                values = _sensor_power_series(rd)
                # Power series are always reported in base Watts.
                if result_md is None:
                    result_md = MetricMetaData(
                        Unit.WATT,
                        Magnitude.ONE,
                        np.dtype("float32"),
                        np.float32(0),
                        np.finfo("float32").max,
                        np.float32(-1),
                    )
            else:
                if rd.v_md.unit != unit:
                    return
                mag_factor = rd.v_md.mag.value / Magnitude.ONE.value
                values = rd.values.astype("float32") * mag_factor
                if result_md is None:
                    result_md = MetricMetaData(
                        rd.v_md.unit,
                        Magnitude.ONE,
                        rd.v_md.dtype,
                        rd.v_md.min,
                        rd.v_md.max,
                        rd.v_md.fill,
                    )
            if values.size > 0:
                series.append(values)
        else:
            for child in n.nodes.values():
                _collect(child)

    _collect(node)

    if not series or result_md is None:
        return None

    all_values = np.concatenate(series)
    return (
        all_values.min(),
        all_values.mean(),
        all_values.max(),
        result_md,
    )


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
