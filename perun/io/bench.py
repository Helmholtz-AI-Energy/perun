"""Bench io module."""

import json
import logging
import pprint as pp

import numpy as np

from perun.data_model.data import DataNode, MetricType, Stats
from perun.data_model.measurement_type import Magnitude, MetricMetaData
from perun.io.text_report import (
    DEFAULT_REGION_METRICS,
    DEFAULT_TABLE_METRICS,
    _parse_group_by,
    _parse_metric_list,
    _parse_stats_list,
)
from perun.io.util import NumpyEncoder, getTFactorMag, raw_metric_stats
from perun.processing import Number

log = logging.getLogger(__name__)


def _bench_unit_factor(
    metric_md: MetricMetaData, bench_units: dict[str, Magnitude], ref_value: Number
) -> tuple[float, Magnitude]:
    """Resolve the scaling factor and magnitude for a bench entry."""
    if metric_md.unit.name in bench_units:
        mag = bench_units[metric_md.unit.name]
        return mag.value / metric_md.mag.value, mag
    return getTFactorMag(ref_value, metric_md)


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

    # Metric/stat/grouping selection is shared with the text report and parsed
    # leniently so a typo or missing option never breaks report generation.
    scriptMetrics = _parse_metric_list(
        mrNode.metadata.get("benchmarking.metrics"), DEFAULT_TABLE_METRICS
    )
    metric_stats = _parse_stats_list(mrNode.metadata.get("benchmarking.metric_stats"))
    group_by = _parse_group_by(mrNode.metadata.get("benchmarking.group_by"))

    bench_units: dict[str, Magnitude] = {
        "JOULE": Magnitude.fromSymbol(mrNode.metadata["benchmarking.units.joule"]),
        "SECOND": Magnitude.fromSymbol(mrNode.metadata["benchmarking.units.second"]),
        "WATT": Magnitude.fromSymbol(mrNode.metadata["benchmarking.units.watt"]),
        "PERCENT": Magnitude.fromSymbol(mrNode.metadata["benchmarking.units.percent"]),
        "BYTE": Magnitude.fromSymbol(mrNode.metadata["benchmarking.units.byte"]),
    }

    log.debug(pp.pformat(bench_units))

    for metricType, metric in mrNode.metrics.items():
        if metricType in scriptMetrics:
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

    # Optional per-device breakdown with min / max taken from the raw sensor
    # time-series. Emitted as additional benchmark entries so downstream tooling
    # can track them individually.
    if group_by == "device" and metric_stats != ["avg"]:
        _appendDeviceStats(
            metricDict, dataNode, mrNode, scriptMetrics, metric_stats, bench_units
        )

    region_data: dict[str, dict[str, tuple[list[int | float], MetricMetaData]]] = {}
    if len(mrNode.nodes) > 1:
        log.info(
            "When generating benchmarks for regions, it is preferable to if each function only runs a single time."
        )

    regionMetrics = _parse_metric_list(
        mrNode.metadata.get("benchmarking.region_metrics"), DEFAULT_REGION_METRICS
    )

    for runNode in mrNode.nodes.values():
        if runNode.regions:
            for region_name, region in runNode.regions.items():
                if region_name not in region_data:
                    region_data[region_name] = {
                        metricType.name: (
                            [stats.mean],
                            stats.metric_md,
                        )
                        for metricType, stats in region.metrics.items()
                        if metricType in regionMetrics
                    }
                else:
                    for metricType, stats in region.metrics.items():
                        if metricType in regionMetrics:
                            region_data[region_name][metricType.name][0].append(
                                stats.mean
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

    log.debug(pp.pformat(metricDict))

    return json.dumps(metricDict, indent=4, cls=NumpyEncoder)


def _appendDeviceStats(
    metricDict: list,
    dataNode: DataNode,
    mrNode: DataNode,
    scriptMetrics: list[MetricType],
    metric_stats: list[str],
    bench_units: dict[str, Magnitude],
) -> None:
    """Append per-device min/max/avg benchmark entries from raw sensor data.

    For every host and device group in each run, the requested statistics are
    computed directly from the underlying sensor time-series (see
    :func:`perun.io.util.raw_metric_stats`) and emitted as individual benchmark
    entries named ``<app>_<mr> - <host>/<device> <METRIC> (<stat>)``.
    """
    want_min = "min" in metric_stats
    want_max = "max" in metric_stats
    want_avg = "avg" in metric_stats

    for runNode in mrNode.nodes.values():
        for hostNode in runNode.nodes.values():
            for deviceGroup in hostNode.nodes.values():
                for metricType in scriptMetrics:
                    raw_stats = raw_metric_stats(deviceGroup, metricType)
                    if raw_stats is None:
                        continue
                    r_min, r_mean, r_max, r_md = raw_stats
                    tfactor, mag = _bench_unit_factor(r_md, bench_units, r_mean)
                    unit_str = f"{mag.symbol}{r_md.unit.symbol}"
                    prefix = (
                        f"{dataNode.id}_{mrNode.id} - "
                        f"{hostNode.id}/{deviceGroup.id} {metricType.name}"
                    )
                    if want_avg:
                        metricDict.append(
                            {
                                "name": f"{prefix} (avg)",
                                "unit": unit_str,
                                "value": r_mean / tfactor,
                            }
                        )
                    if want_min:
                        metricDict.append(
                            {
                                "name": f"{prefix} (min)",
                                "unit": unit_str,
                                "value": r_min / tfactor,
                            }
                        )
                    if want_max:
                        metricDict.append(
                            {
                                "name": f"{prefix} (max)",
                                "unit": unit_str,
                                "value": r_max / tfactor,
                            }
                        )
