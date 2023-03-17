"""Bench io module."""
import json

from perun.data_model.data import DataNode, MetricType, Stats
from perun.util import value2str

lessIsBetterMetrics = [MetricType.RUNTIME, MetricType.ENERGY]


def exportBench(dataNode: DataNode) -> str:
    """Export data node to json format based on the github continuous benchmark action.

    https://github.com/benchmark-action/github-action-benchmark

    Args:
        dataNode (DataNode): Perun results

    Returns:
        str: Output string
    """
    metricDict = []
    for metricType, metric in dataNode.metrics.items():
        if metricType in lessIsBetterMetrics:
            metric_md = metric.metric_md
            value, tfactor, mag = value2str(metric.value, metric_md)

            if isinstance(metric, Stats):
                metricDict.append(
                    {
                        "name": f"{dataNode.metadata['app_name']} - {metricType.name}",
                        "unit": f"{mag.symbol}{metric_md.unit.symbol}",
                        "value": metric.mean / tfactor,
                        "range": metric.std / tfactor,
                    }
                )
            else:
                metricDict.append(
                    {
                        "name": f"{dataNode.metadata['app_name']} - {metricType.name}",
                        "unit": f"{mag.symbol}{metric_md.unit.symbol}",
                        "value": metric.value / tfactor,
                    }
                )

    return json.dumps(metricDict, indent=4)
