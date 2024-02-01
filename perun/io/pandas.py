"""Pandas IO module."""

from pathlib import Path
from typing import Any, List, Tuple

import pandas as pd

from perun.data_model.data import DataNode


def exportCSV(outputPath: Path, dataNode: DataNode, mr_id: str):
    """Export data node to csv format.

    Parameters
    ----------
    outputPath : Path
        Path to export data to.
    dataNode : DataNode
        Perun data node.
    mr_id : str
        Id of Multi_run node to get data from
    """
    columns = [
        "run id",
        "hostname",
        "device_group",
        "sensor",
        "unit",
        "magnitude",
        "timestep",
        "value",
    ]

    rows = []
    mrNode = dataNode.nodes[mr_id]
    for run_n, runNode in mrNode.nodes.items():
        rows.extend(_rowsFromRunNode(runNode, run_n))

    df = pd.DataFrame(rows, columns=columns)
    df.to_csv(outputPath)


def _rowsFromRunNode(runNode: DataNode, run_n: int) -> List[Tuple[Any, ...]]:
    """Create table rows from a RUN type data node.

    Parameters
    ----------
    runNode : DataNode
        RUN type node
    run_n : int
        Id number of data node

    Returns
    -------
    List[Tuple[Any, ...]]
        List of tuples with table entries.
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
                                run_n,
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
