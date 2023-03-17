"""Pandas IO module."""
from pathlib import Path
from typing import Any, List, Tuple

import pandas as pd

from perun.data_model.data import DataNode, NodeType


def exportCSV(outputPath: Path, dataNode: DataNode):
    """Export all raw data collected to a csv file using pandas.

    Args:
        outputPath (Path): Output path
        dataNode (DataNode): Perun data node with raw data.
    """
    df = _dataNode2Pandas(dataNode)
    df.to_csv(outputPath)


def _dataNode2Pandas(dataNode: DataNode) -> pd.DataFrame:
    """Create a pandas dataframe for Data Node raw data.

    Args:
        dataNode (DataNode): Perun Data Node

    Returns:
        pd.DataFrame: DataFrame
    """
    columns = [
        "app_name",
        "run_id",
        "hostname",
        "device_group",
        "sensor",
        "unit",
        "magnitude",
        "timestep",
        "value",
    ]

    rows = []
    exp_name = dataNode.metadata["app_name"]
    if dataNode.type == NodeType.MULTI_RUN:
        for id, node in dataNode.nodes.items():
            rows.extend(_rowsFromRunNode(node, exp_name, id))

    else:
        id = dataNode.id
        rows = _rowsFromRunNode(dataNode, exp_name, id)

    return pd.DataFrame(rows, columns=columns)


def _rowsFromRunNode(
    runNode: DataNode, app_name: str, run_id: str
) -> List[Tuple[Any, ...]]:
    """Read raw data from data nodes and arrange it as rows.

    Args:
        runNode (DataNode): Data node.
        app_name (str): Application name.
        run_id (str): Run id.

    Returns:
        List[Tuple[Any]]: Rows with raw data.
    """
    rows: List[Tuple[Any, ...]] = []
    for hostId, hostNode in runNode.nodes.items():
        for deviceGroupId, deviceGroupNode in hostNode.nodes.items():
            for sensorId, sensorNode in deviceGroupNode.nodes.items():
                if sensorNode.raw_data is not None:
                    rawData = sensorNode.raw_data
                    unit = rawData.v_md.unit.value
                    mag = rawData.v_md.mag.value
                    for i in range(len(rawData.timesteps)):
                        rows.append(
                            (
                                app_name,
                                run_id,
                                hostId,
                                deviceGroupId,
                                sensorId,
                                unit,
                                mag,
                                rawData.timesteps[i],
                                rawData.values[i],
                            )
                        )

    return rows
