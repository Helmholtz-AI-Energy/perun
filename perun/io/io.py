"""IO Module."""

import enum
from pathlib import Path
from typing import Optional, Union

from perun import log
from perun.data_model.data import DataNode, NodeType
from perun.io.bench import exportBench
from perun.io.hdf5 import exportHDF5, importHDF5
from perun.io.json import exportJson, importJson
from perun.io.pandas import exportCSV
from perun.io.pickle import exportPickle, importPickle
from perun.io.text_report import textReport

_suffixes = {
    "text": "txt",
    "yaml": "yaml",
    "json": "json",
    "hdf5": "hdf5",
    "pickle": "pkl",
    "csv": "csv",
    "bench": "json",
}


class IOFormat(enum.Enum):
    """Available IO file formats."""

    TEXT = "text"
    JSON = "json"
    HDF5 = "hdf5"
    PICKLE = "pickle"
    CSV = "csv"
    BENCH = "bench"
    # YAML = "yaml"

    @property
    def suffix(self):
        """Return file suffix from format."""
        return _suffixes[self.value]

    @classmethod
    def fromSuffix(cls, suffix: str):
        """Return format from suffix."""
        for key, value in _suffixes.items():
            if value in suffix:
                return cls(key)
        raise ValueError("Invalid file format.")


def exportTo(
    data_out: Path,
    dataNode: DataNode,
    format: IOFormat,
    rawData: bool = False,
    depth: Optional[int] = None,
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

    if format == IOFormat.BENCH and dataNode.type != NodeType.MULTI_RUN:
        log.warning(
            "BENCH format can only be used with 'bench' mode enabled. Using pickle instead."
        )
        format = IOFormat.PICKLE

    filename = f"{dataNode.metadata['app_name']}_{dataNode.id}"

    reportStr: Union[str, bytes]
    if format == IOFormat.JSON:
        filename += ".json"
        fileType = "w"
        reportStr = exportJson(dataNode, depth, rawData)
        with open(data_out / filename, fileType) as file:
            file.write(reportStr)
    elif format == IOFormat.HDF5:
        filename += ".hdf5"
        exportHDF5(data_out / filename, dataNode)
    elif format == IOFormat.PICKLE:
        filename += ".pkl"
        fileType = "wb"
        reportStr = exportPickle(dataNode)
        with open(data_out / filename, fileType) as file:
            file.write(reportStr)
    elif format == IOFormat.CSV:
        filename += ".cvs"
        exportCSV(data_out / filename, dataNode)
    elif format == IOFormat.BENCH:
        filename += ".json"
        fileType = "w"
        reportStr = exportBench(dataNode)
        with open(data_out / filename, fileType) as file:
            file.write(reportStr)
    # elif format == IOFormat.YAML:
    #     filename += ".yaml"
    #     reportStr = exportYaml(dataNode, depth, rawData)
    else:
        filename += ".txt"
        fileType = "w"
        reportStr = textReport(dataNode)
        with open(data_out / filename, fileType) as file:
            file.write(reportStr)


def importFrom(filePath: Path, format: IOFormat) -> DataNode:
    """Import DataNode structure from path. If no format is given, it is inferred form path sufix.

    Args:
        filePath (Path): Path to file
        format (Optional[IOFormat], optional): File format. Defaults to None.
    """
    if format == IOFormat.JSON:
        with open(filePath, "r") as file:
            dataNode = importJson(file.read())
    # elif format == IOFormat.YAML:
    #     filename += ".yaml"
    #     reportStr = exportYaml(dataNode, depth, rawData)
    elif format == IOFormat.HDF5:
        dataNode = importHDF5(filePath)
    elif format == IOFormat.PICKLE:
        with open(filePath, "rb") as file:
            dataNode = importPickle(file.read())
    else:
        raise ValueError("File format is not supported.")

    return dataNode
