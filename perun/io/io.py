"""IO Module."""

import enum
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from perun import log
from perun.data_model.data import DataNode
from perun.io.bench import exportBench
from perun.io.hdf5 import exportHDF5, importHDF5
from perun.io.json import exportJson, importJson
from perun.io.pandas import exportCSV
from perun.io.pickle import exportPickle, importPickle
from perun.io.text_report import textReport

_suffixes = {
    "text": "txt",
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
    output_path: Path, dataNode: DataNode, format: IOFormat, mr_id: Optional[str] = None
):
    """Export DataNode structure to the selected format.

    :param data_out: Output path
    :type data_out: Path
    :param dataNode: DataNode tree with processed metrics
    :type dataNode: DataNode
    :param format: Output format.
    :type format: IOFormat
    """
    if not dataNode.processed:
        log.warning("Data has not been processed before import. Proceed with caution.")
        raise Exception("DataNode needs to be processed before it can be exported.")

    if not output_path.parent.exists():
        log.info(f"{output_path.parent} does not exists. So lets make it.")
        output_path.parent.mkdir()

    if not mr_id and (
        format == IOFormat.BENCH or format == IOFormat.TEXT or format == IOFormat.CSV
    ):
        log.warning("No run ID provided, using last executed run to generate output")
        last_dt = datetime.min
        for node in dataNode.nodes.values():
            exec_dt = datetime.fromisoformat(node.metadata["execution_dt"])
            if exec_dt > last_dt:
                last_dt = exec_dt
                mr_id = node.id

    elif mr_id not in dataNode.nodes:
        log.error("Non existent run id")
        raise Exception("Cannot generate report with non existent id.")

    reportStr: Union[str, bytes]
    if format == IOFormat.JSON:
        fileType = "w"
        output_path = output_path / f"{dataNode.id}.{format.suffix}"

        if output_path.exists() and output_path.is_file():
            log.warn(f"Overwriting existing file {output_path}")

        reportStr = exportJson(dataNode)
        with open(output_path, fileType) as file:
            file.write(reportStr)

    elif format == IOFormat.HDF5:
        output_path = output_path / f"{dataNode.id}.{format.suffix}"

        if output_path.exists() and output_path.is_file():
            log.warn(f"Overwriting existing file {output_path}")

        exportHDF5(output_path, dataNode)

    elif format == IOFormat.PICKLE:
        fileType = "wb"

        output_path = output_path / f"{dataNode.id}.{format.suffix}"

        if output_path.exists() and output_path.is_file():
            log.warn(f"Overwriting existing file {output_path}")

        reportStr = exportPickle(dataNode)
        with open(output_path, fileType) as file:
            file.write(reportStr)

    elif format == IOFormat.CSV:
        output_path = output_path / f"{dataNode.id}_{mr_id}.{format.suffix}"

        if output_path.exists() and output_path.is_file():
            log.warn(f"Overwriting existing file {output_path}")

        exportCSV(output_path, dataNode, mr_id)  # type: ignore
    elif format == IOFormat.BENCH:
        fileType = "w"
        output_path = output_path / f"{dataNode.id}_{mr_id}.{format.suffix}"

        if output_path.exists() and output_path.is_file():
            log.warn(f"Overwriting existing file {output_path}")

        reportStr = exportBench(dataNode, mr_id)  # type: ignore
        with open(output_path, fileType) as file:
            file.write(reportStr)

    elif format == IOFormat.TEXT:
        fileType = "w"
        output_path = output_path / f"{dataNode.id}_{mr_id}.{format.suffix}"

        if output_path.exists() and output_path.is_file():
            log.warn(f"Overwriting existing file {output_path}")

        reportStr = textReport(dataNode, mr_id)  # type: ignore
        with open(output_path, fileType) as file:
            file.write(reportStr)


def importFrom(filePath: Path, format: IOFormat) -> DataNode:
    """Import DataNode structure from path. If no format is given, it is inferred from the file suffix.

    :param filePath: Path to file
    :type filePath: Path
    :param format: File format
    :type format: IOFormat
    :return: Perun DataNode structure
    :rtype: DataNode
    """
    if format == IOFormat.JSON:
        with open(filePath, "r") as file:
            dataNode = importJson(file.read())
    elif format == IOFormat.HDF5:
        dataNode = importHDF5(filePath)
    elif format == IOFormat.PICKLE:
        with open(filePath, "rb") as file:
            dataNode = importPickle(file.read())
    else:
        raise ValueError("File format is not supported.")

    return dataNode
