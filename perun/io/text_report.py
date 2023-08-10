"""Text report module."""
import pandas as pd

from perun import log
from perun.data_model.data import DataNode, MetricType, NodeType, Stats
from perun.io.util import value2str


def textReport(dataNode: DataNode, mr_id: str) -> str:
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
        f"App name: {dataNode.metadata['app_name']}\n"
        f"First run: {dataNode.metadata['creation_dt']}\n"
        f"Last run: {dataNode.metadata['last_execution_dt']}\n"
        "\n"
    )

    # Host and device table
    rows = []
    mr_node: DataNode = dataNode.nodes[mr_id]

    for run_number, run_node in mr_node.items():
        for host_name, host_node in run_node.items():
            entry = {
                "#": run_number,
                "host": host_name,
            }
            for metric_id, metric in host_node.metrics.items():
                value, tfactor, mag = value2str(metric.value, metric.metric_md)
                unit_str = f"{mag.symbol}{metric.metric_md.unit.value}"
                entry[metric_id] = value + unit_str

            rows.append(entry)

    mr_table = pd.DataFrame.from_records(rows).to_markdown()
    mr_report_str = f"RUN ID: {mr_id}\n" + mr_table + "\n"

    # Regions

    reportStr += f"\nThe application used a total of {e_kWh:.3f} kWh, released a total of {kgCO2:.3f} kgCO2eq into the atmosphere, and you paid {euro:.2f} € for it.\n"

    return reportStr
