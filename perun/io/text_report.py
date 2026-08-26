"""Text report module."""

import logging
from typing import Any

import pandas as pd

from perun.data_model.data import DataNode, MetricType, Stats
from perun.io.util import dataframe_to_markdown, value2MeanStdStr, value2ValueUnitStr

log = logging.getLogger(__name__)

# Default columns for the host/device table, used when the configuration does
# not specify a `benchmarking.metrics` value.
DEFAULT_TABLE_METRICS = [
    MetricType.RUNTIME,
    MetricType.ENERGY,
    MetricType.POWER,
    MetricType.CPU_POWER,
    MetricType.CPU_UTIL,
    MetricType.GPU_POWER,
    MetricType.GPU_MEM,
    MetricType.DRAM_POWER,
    MetricType.DRAM_MEM,
]

# Default region metrics, used when the configuration does not specify a
# `benchmarking.region_metrics` value.
DEFAULT_REGION_METRICS = [
    MetricType.RUNTIME,
    MetricType.POWER,
    MetricType.CPU_UTIL,
    MetricType.DRAM_MEM,
    MetricType.GPU_MEM,
]

# Friendly column headers for region metrics; any metric not listed falls back
# to a generic "Avg <NAME>" label.
_REGION_METRIC_LABELS = {
    MetricType.RUNTIME: "Avg Runtime",
    MetricType.POWER: "Avg Power",
    MetricType.CPU_UTIL: "Avg CPU Util",
    MetricType.DRAM_MEM: "Avg RAM Mem Util",
    MetricType.GPU_MEM: "Avg GPU Mem Util",
}


def _parse_metric_list(raw: str | None, defaults: list[MetricType]) -> list[MetricType]:
    """Parse a comma/space separated metric list from the configuration.

    Unknown metric names are skipped with a warning (lenient behaviour) rather
    than raising, so a typo in the configuration never breaks report
    generation.

    Parameters
    ----------
    raw : str | None
        Raw configuration value (e.g. ``"runtime,energy"``). If ``None`` or
        empty, ``defaults`` is returned.
    defaults : list[MetricType]
        Fallback list used when ``raw`` is empty.

    Returns
    -------
    list[MetricType]
        Resolved, de-duplicated list of metric types.
    """
    if not raw or not raw.strip():
        return list(defaults)

    tokens = [tok.strip() for tok in raw.replace(",", " ").split()]
    resolved: list[MetricType] = []
    for token in tokens:
        if not token:
            continue
        try:
            metric = MetricType(token.lower())
        except ValueError:
            log.warning(
                "Unknown metric '%s' in report configuration; skipping it.", token
            )
            continue
        if metric not in resolved:
            resolved.append(metric)
    # If every configured metric was invalid, fall back to the defaults so the
    # report is never left without any columns.
    return resolved if resolved else list(defaults)


def _region_metric_label(metric: MetricType) -> str:
    """Return a human friendly column label for a region metric."""
    return _REGION_METRIC_LABELS.get(metric, f"Avg {metric.name}")


def textReport(dataNode: DataNode, mr_id: str) -> str:
    """Create text report from selected MULTI_RUN node.

    Parameters
    ----------
    dataNode : DataNode
        Application data node
    mr_id : str
        Multirun id

    Returns
    -------
    str
        Report string
    """
    if not dataNode.processed:
        log.error("Data has not been processed, unable to create report.")
        raise Exception("Cannot generate report from unprocessed data node.")

    if mr_id not in dataNode.nodes:
        log.error("Non existent run id")
        raise Exception("Cannot generate report with non existent id.")

    # Report header
    report_header = (
        "PERUN REPORT\n"
        "\n"
        f"App name: {dataNode.id}\n"
        f"First run: {dataNode.metadata['creation_dt']}\n"
        f"Last run: {dataNode.metadata['last_execution_dt']}\n"
        "\n\n"
    )

    # Host and device table
    host_device_rows = []
    region_rows = []
    mr_node: DataNode = dataNode.nodes[mr_id]

    # Which metrics to show is driven by the perun configuration, which is
    # persisted in the MULTI_RUN node metadata as "<section>.<option>" keys.
    # Unknown metric names are skipped leniently (see _parse_metric_list).
    table_metrics = _parse_metric_list(
        mr_node.metadata.get("benchmarking.metrics"), DEFAULT_TABLE_METRICS
    )
    region_metrics = _parse_metric_list(
        mr_node.metadata.get("benchmarking.region_metrics"), DEFAULT_REGION_METRICS
    )

    for run_number, run_node in mr_node.nodes.items():
        if run_node.regions:
            for region_name, region in run_node.regions.items():
                if region.processed:
                    row = {
                        "Round #": run_node.id,
                        "Function": region_name,
                        "Avg Calls / Rank": region.runs_per_rank.mean,
                    }
                    row.update(
                        {
                            _region_metric_label(metric_type): value2MeanStdStr(stats)
                            for metric_type, stats in region.metrics.items()
                            if metric_type in region_metrics
                        }
                    )
                    region_rows.append(row)
        for host_name, host_node in run_node.nodes.items():
            entry = {
                "Round #": run_number,
                "Host": host_name,
            }
            for metric_type in table_metrics:
                if metric_type in host_node.metrics:
                    m = host_node.metrics[metric_type]
                    entry[metric_type.name] = value2ValueUnitStr(m.value, m.metric_md)

            host_device_rows.append(entry)
        entry = {"Round #": run_number, "Host": "All"}
        for metric_type in table_metrics:
            if metric_type in run_node.metrics:
                m = run_node.metrics[metric_type]
                entry[metric_type.name] = value2ValueUnitStr(m.value, m.metric_md)

        host_device_rows.append(entry)

    mr_table = pd.DataFrame.from_records(host_device_rows).sort_values(
        by=["Host", "Round #"]
    )
    mr_report_str = f"RUN ID: {mr_id}\n\n" + dataframe_to_markdown(mr_table) + "\n\n"

    # Regions
    if len(region_rows) > 0:
        region_table = pd.DataFrame.from_records(region_rows).sort_values(
            by=["Function", "Round #"]
        )
        region_report_str = (
            "Monitored Functions\n\n" + dataframe_to_markdown(region_table) + "\n\n"
        )
    else:
        region_report_str = ""

    n_runs = len(dataNode.nodes)
    if MetricType.ENERGY in dataNode.metrics and isinstance(
        dataNode.metrics[MetricType.ENERGY], Stats
    ):
        stats: Stats = dataNode.metrics[MetricType.ENERGY]  # type: ignore[assignment]

        # Application Summary
        total_energy = stats.sum
        e_kWh = total_energy / (3600 * 1e3)
        kgCO2 = dataNode.metrics[MetricType.CO2].sum / 1e3  # type: ignore[union-attr]
        money = dataNode.metrics[MetricType.MONEY].sum  # type: ignore[union-attr]
        money_icon = mr_node.metadata["post-processing.price_unit"]

        app_summary_str = f"Application Summary\n\nThe application has been run {n_runs} times. In total, it has used {e_kWh:.3f} kWh, released a total of {kgCO2:.3f} kgCO2e into the atmosphere, and you paid {money:.2f} {money_icon} in electricity for it."
    else:
        app_summary_str = f"The application has been run {n_runs} times."

    return report_header + mr_report_str + region_report_str + app_summary_str


def sensors_table(sensors: list[dict[str, Any]], by_rank: bool = True) -> str:
    """Create a text table from a list of sensor readings.

    Parameters
    ----------
    sensors : list[dict[str, Any]]
        List of sensor readings
    by_rank: bool, optional
        If the table should separate available sensors by rank.

    Returns
    -------
    str
        Table string
    """
    if not sensors:
        return "No sensor data available."

    result = ""
    if by_rank:
        for rank, rank_sensors in enumerate(sensors):
            result += f"RANK {rank}:\n"

            table = dataframe_to_markdown(
                pd.DataFrame.from_dict(
                    rank_sensors, orient="index", columns=["Source", "Device", "Unit"]
                )
                .reset_index()
                .rename(columns={"index": "Sensor"})
                .sort_values(by=["Source", "Sensor"])
            )
            result += table + "\n\n"

    else:
        table = dataframe_to_markdown(
            pd.DataFrame.from_dict(
                sensors[0], orient="index", columns=["Source", "Device", "Unit"]
            )
            .reset_index()
            .rename(columns={"index": "Sensor"})
            .sort_values(by=["Source", "Sensor"])
        )
        result += table + "\n"

    return result
