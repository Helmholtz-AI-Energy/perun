"""Text report module."""

from datetime import timedelta
from typing import Tuple

import numpy as np
from prettytable import PrettyTable

from perun import log
from perun.data_model.data import DataNode, MetricType, NodeType, Stats
from perun.data_model.measurement_type import Magnitude, MetricMetaData, Unit


def textReport(dataNode: DataNode) -> str:
    """
    Create text report from based on root node of the DataNode tree.

    Args:
        dataNode: Root of DataNode tree.

    Returns:
        str: txt report
    """
    if dataNode.type != NodeType.MULTI_RUN and dataNode.type != NodeType.RUN:
        log.error(
            "Text reports are meant for only to get a brief overview of individual runs or of benchmark results over multiple runs."
        )
        raise Exception("Invalid dataNode type.")

    if not dataNode.processed:
        log.error("Data has not been processed, unable to create report.")
        raise Exception("Cannot generate report from unprocessed data node.")

    reportStr = (
        "------------------------------------------\n"
        "PERUN REPORT\n"
        "\n"
        f"App name: {dataNode.metadata['app_name']}\n"
        f"Run ID: {dataNode.id}\n"
    )

    if dataNode.type == NodeType.MULTI_RUN:
        table = PrettyTable(float_format="1.3f")
        table.field_names = ["Name", "mean", "std", "max", "min"]
        table.align = "r"
        table.align["Name"] = "l"  # type: ignore
        for metricType in MetricType:
            if metricType in dataNode.metrics:
                metric = dataNode.metrics[metricType]
                if isinstance(metric, Stats):
                    value, tfactor, mag = value2str(metric.value, metric.metric_md)
                    table.add_row(
                        [
                            f"{metricType.name} [{mag.symbol()}{metric.metric_md.unit.value}]",
                            f"{metric.mean / tfactor:.3f}",
                            f"{metric.std / tfactor:.3f}",
                            f"{metric.max / tfactor:.3f}",
                            f"{metric.min / tfactor:.3f}",
                        ]
                    )
        reportStr += "\n"
        reportStr += table.get_string(float_format=".3")

    else:
        for metricType in MetricType:
            if metricType in dataNode.metrics:
                metric = dataNode.metrics[metricType]
                value, _, mag = value2str(metric.value, metric.metric_md)
                reportStr += f"{metricType.name}: {value} {mag.symbol()}{metric.metric_md.unit.value}\n"

    return reportStr


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
