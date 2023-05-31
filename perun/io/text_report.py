"""Text report module."""


from perun import config, log
from perun.data_model.data import DataNode, MetricType, NodeType, Stats
from perun.util import value2str


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
        columns = ["Name", "Unit", "mean", "std", "max", "min"]
        column_widths = [4, 4, 8, 8, 8, 8]
        entries = {}
        for metricType in MetricType:
            if metricType in dataNode.metrics:
                metric = dataNode.metrics[metricType]
                if isinstance(metric, Stats):
                    value, tfactor, mag = value2str(metric.value, metric.metric_md)
                    unit_str = f"{mag.symbol}{metric.metric_md.unit.value}"
                    column_widths[0] = (
                        column_widths[0]
                        if column_widths[0] > len(metricType.name)
                        else len(metricType.name)
                    )
                    column_widths[1] = (
                        column_widths[1]
                        if column_widths[1] > len(unit_str)
                        else len(unit_str)
                    )
                    entries[metricType.name] = [
                        unit_str,
                        f"{metric.mean/tfactor:.3f}",
                        f"{metric.std/tfactor:.3f}",
                        f"{metric.max/tfactor:.3f}",
                        f"{metric.min/tfactor:.3f}",
                    ]

        reportStr += "\n"
        header_row: str = "|" + "".join(
            [
                " {0:^{width}} |".format(column, width=width)
                for column, width in zip(columns, column_widths)
            ]
        )
        table_width = len(header_row)
        reportStr += header_row + "\n"
        reportStr += ("-" * table_width) + "\n"
        for key, values in entries.items():
            name = "| {0:<{width}} |".format(key, width=column_widths[0])
            values_str = "".join(
                [
                    " {0:>{w}} |".format(v, w=w)
                    for v, w in zip(values, column_widths[1:])
                ]
            )
            reportStr += name + values_str + "\n"

    else:
        for metricType in MetricType:
            if metricType in dataNode.metrics:
                metric = dataNode.metrics[metricType]
                value, _, mag = value2str(metric.value, metric.metric_md)
                reportStr += f"{metricType.name}: {value} {mag.symbol}{metric.metric_md.unit.value}\n"

        if MetricType.ENERGY in dataNode.metrics:
            e_metric = dataNode.metrics[MetricType.ENERGY]
            e_pue = e_metric.value * config.getfloat("post-processing", "pue")
            e_kWh = e_pue / (3600 * 1e3)
            kgCO2 = e_kWh * config.getfloat("post-processing", "emissions_factor") / 1e3
            euro = e_kWh * config.getfloat("post-processing", "price_factor") / 1e2

            reportStr += f"\nThe application used a total of {e_kWh:.3f} kWh, released a total of {kgCO2:.3f} kgCO2eq into the atmosphere, and you paid {euro:.2f} € for it.\n"

    return reportStr
