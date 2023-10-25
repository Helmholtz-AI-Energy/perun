"""Text report module."""
import pandas as pd

from perun import config, log
from perun.data_model.data import DataNode, MetricType
from perun.io.util import value2MeanStdStr, value2ValueUnitStr

tableMetrics = [
    MetricType.RUNTIME,
    MetricType.ENERGY,
    MetricType.POWER,
    MetricType.CPU_POWER,
    MetricType.CPU_UTIL,
    MetricType.GPU_POWER,
    MetricType.GPU_MEM,
    MetricType.DRAM_POWER,
    MetricType.MEM_UTIL,
]


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

    for run_number, run_node in mr_node.nodes.items():
        if run_node.regions:
            for region_name, region in run_node.regions.items():
                if region.processed:
                    region_rows.append(
                        {
                            "Round #": run_node.id,
                            "Function": region_name,
                            "Avg Calls / Rank": region.runs_per_rank.mean,
                            "Avg Runtime": value2MeanStdStr(region.runtime),
                            "Avg Power": value2MeanStdStr(region.power),
                            "Avg CPU Util": value2MeanStdStr(region.cpu_util),
                            "Avg GPU Mem Util": value2MeanStdStr(region.gpu_util),
                        }
                    )
        for host_name, host_node in run_node.nodes.items():
            entry = {
                "Round #": run_number,
                "Host": host_name,
            }
            for metric_type in tableMetrics:
                if metric_type in host_node.metrics:
                    m = host_node.metrics[metric_type]
                    entry[metric_type.name] = value2ValueUnitStr(m.value, m.metric_md)

            host_device_rows.append(entry)
        entry = {"Round #": run_number, "Host": "All"}
        for metric_type in tableMetrics:
            if metric_type in run_node.metrics:
                m = run_node.metrics[metric_type]
                entry[metric_type.name] = value2ValueUnitStr(m.value, m.metric_md)

        host_device_rows.append(entry)

    mr_table = pd.DataFrame.from_records(host_device_rows).sort_values(by="Host")
    mr_report_str = f"RUN ID: {mr_id}\n\n" + mr_table.to_markdown(index=False) + "\n\n"

    # Regions
    if len(region_rows) > 0:
        region_table = pd.DataFrame.from_records(region_rows).sort_values("Function")
        region_report_str = (
            "Monitored Functions\n\n" + region_table.to_markdown(index=False) + "\n\n"
        )
    else:
        region_report_str = ""

    n_runs = len(dataNode.nodes)
    if MetricType.ENERGY in dataNode.metrics:
        # Application Summary
        total_energy = dataNode.metrics[MetricType.ENERGY].sum  # type: ignore
        e_kWh = total_energy / (3600 * 1e3)
        kgCO2 = dataNode.metrics[MetricType.CO2].sum  # type: ignore
        money = dataNode.metrics[MetricType.MONEY].sum  # type: ignore
        money_icon = config.get("post-processing", "price_unit")

        app_summary_str = f"Application Summary\n\nThe application has been run {n_runs} times. Throughout its runtime, it has used {e_kWh:.3f} kWh, released a total of {kgCO2:.3f} kgCO2e into the atmosphere, and you paid {money:.2f} {money_icon} in electricity for it."
    else:
        app_summary_str = f"The application has been run {n_runs} times."

    return report_header + mr_report_str + region_report_str + app_summary_str
