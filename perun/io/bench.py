"""Bench io module."""
import json
import logging
from typing import Dict, List, Tuple

import numpy as np

from perun.data_model.data import DataNode, MetricType, Stats
from perun.data_model.measurement_type import Magnitude, MetricMetaData
from perun.io.util import getTFactorMag

log = logging.getLogger("perun")


lessIsBetterMetrics = [MetricType.RUNTIME, MetricType.ENERGY]


def exportBench(dataNode: DataNode, mr_id: str) -> str:
    """Export data node to json format based on the github continuous benchmark action.

    https://github.com/benchmark-action/github-action-benchmark

    Parameters
    ----------
    dataNode : DataNode
        Data Node
    mr_id : str
        MULTI_RUN node to get data from.

    Returns
    -------
    str
        Json string with benchmark data.
    """
    metricDict = []
    mrNode = dataNode.nodes[mr_id]

    bench_units: Dict[str, Magnitude] = {
        "JOULE": Magnitude.fromSymbol(mrNode.metadata["benchmarking.units.joule"]),
        "SECOND": Magnitude.fromSymbol(mrNode.metadata["benchmarking.units.second"]),
        "WATT": Magnitude.fromSymbol(mrNode.metadata["benchmarking.units.power"]),
        "PERCENT": Magnitude.fromSymbol(mrNode.metadata["benchmarking.units.percent"]),
    }

    for metricType, metric in mrNode.metrics.items():
        if metricType in lessIsBetterMetrics:
            metric_md: MetricMetaData = metric.metric_md
            if metric_md.unit.name in bench_units:
                mag = bench_units[metric_md.unit.name]
                old_mag = metric_md.mag
                tfactor = mag.value / old_mag.value
            else:
                tfactor, mag = getTFactorMag(metric.value, metric_md)

            if isinstance(metric, Stats):
                metricDict.append(
                    {
                        "name": f"{dataNode.id}_{mrNode.id} - {metricType.name}",
                        "unit": f"{mag.symbol}{metric_md.unit.symbol}",
                        "value": metric.mean / tfactor,
                        "range": metric.std / tfactor,
                    }
                )
            else:
                metricDict.append(
                    {
                        "name": f"{dataNode.id}_{mrNode.id} - {metricType.name}",
                        "unit": f"{mag.symbol}{metric_md.unit.symbol}",
                        "value": metric.value / tfactor,
                    }
                )

    region_data: Dict[str, Dict[str, Tuple[List[np.number], MetricMetaData]]] = {}
    if len(mrNode.nodes) > 1:
        log.info(
            "When generating benchmarks for regions, it is preferable to if each function only runs a single time."
        )

    for runNode in mrNode.nodes.values():
        if runNode.regions:
            for region_name, region in runNode.regions.items():
                if region_name not in region_data:
                    region_data[region_name] = {
                        MetricType.RUNTIME.name: (
                            [region.runtime.mean],
                            region.runtime.metric_md,
                        ),
                        MetricType.POWER.name: (
                            [region.power.mean],
                            region.power.metric_md,
                        ),
                        MetricType.CPU_UTIL.name: (
                            [region.cpu_util.mean],
                            region.cpu_util.metric_md,
                        ),
                        MetricType.GPU_UTIL.name: (
                            [region.gpu_util.mean],
                            region.gpu_util.metric_md,
                        ),
                    }
                else:
                    region_data[region_name][MetricType.RUNTIME.name][0].append(
                        region.runtime.mean
                    )
                    region_data[region_name][MetricType.POWER.name][0].append(
                        region.power.mean
                    )
                    region_data[region_name][MetricType.CPU_UTIL.name][0].append(
                        region.cpu_util.mean
                    )
                    region_data[region_name][MetricType.GPU_UTIL.name][0].append(
                        region.gpu_util.mean
                    )

    for region_name, region in region_data.items():
        for metric_name, data in region.items():
            values = data[0]
            metadata = data[1]
            if len(values) > 1:
                mean = np.mean(values)
                std = np.std(values)
                if metadata.unit.name in bench_units:
                    mag = bench_units[metadata.unit.name]
                    old_mag = metadata.mag
                    tfactor = mag.value / old_mag.value
                else:
                    tfactor, mag = getTFactorMag(mean, metadata)
                metricDict.append(
                    {
                        "name": f"{region_name}_{mr_id} - {metric_name}",
                        "unit": f"{mag.symbol}{metadata.unit.symbol}",
                        "value": mean / tfactor,
                        "range": std / tfactor,
                    }
                )
            else:
                value = values[0]
                if metadata.unit.name in bench_units:
                    mag = bench_units[metadata.unit.name]
                    old_mag = metadata.mag
                    tfactor = mag.value / old_mag.value
                else:
                    tfactor, mag = getTFactorMag(value, metadata)
                metricDict.append(
                    {
                        "name": f"{region_name}_{mr_id} - {metric_name}",
                        "unit": f"{mag.symbol}{metadata.unit.symbol}",
                        "value": value / tfactor,
                    }
                )

    return json.dumps(metricDict, indent=4)
