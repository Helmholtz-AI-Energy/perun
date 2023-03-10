"""IO Module."""

import enum
from pathlib import Path
from typing import Optional

from perun import log
from perun.data_model.data import DataNode, NodeType
from perun.io.text_report import textReport


class IOFormat(enum.Enum):
    """Available IO file formats."""

    TEXT = "text"
    YAML = "yaml"
    JSON = "json"
    HDF5 = "hdf5"
    PICKLE = "pickle"
    PANDAS = "pandas"


def exportTo(
    data_out: Path,
    dataNode: DataNode,
    format: IOFormat = IOFormat.TEXT,
    rawData: bool = False,
    depth: NodeType = NodeType.RUN,
):
    """Export DataNode structure to the selected format.

    Args:
        dataNode (DataNode): DataNode tree with processed metrics.
        format (IOFormat, optional): Output format. Defaults to IOFormat.TEXT.
        rawData (bool, optional): If raw data should be included. Limits available formats. Defaults to False.
    """
    if not dataNode.processed:
        log.warning("Data has not been processed before import. Proceed with caution.")
        raise Exception("DataNode needs to be processed before it can be exported.")

    if not data_out.exists():
        log.info(f"{data_out} does not exists. So lets make it.")
        data_out.mkdir()

    if format == IOFormat.YAML:
        pass
    elif format == IOFormat.JSON:
        pass
    elif format == IOFormat.HDF5:
        pass
    elif format == IOFormat.PICKLE:
        pass
    elif format == IOFormat.PANDAS:
        pass
    else:
        filename = f"{dataNode.metadata['app_name']}_{dataNode.id}.txt"
        reportStr = textReport(dataNode)
        with open(data_out / filename, "w") as file:
            file.write(reportStr)


def importFrom(filePath: Path, format: Optional[IOFormat] = None):
    """Import DataNode structure from path. If no format is given, it is inferred form path sufix.

    Args:
        filePath (Path): Path to file
        format (Optional[IOFormat], optional): File format. Defaults to None.
    """
    pass
