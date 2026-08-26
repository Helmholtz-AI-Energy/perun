"""IO Util."""

import json
from collections.abc import Sequence
from typing import Any, Tuple

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
