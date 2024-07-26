"""IO Module."""

import enum
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from perun.data_model.data import DataNode
from perun.io.bench import exportBench
from perun.io.hdf5 import exportHDF5, importHDF5
from perun.io.json import exportJson, importJson
from perun.io.pandas import exportCSV
from perun.io.pickle import exportPickle, importPickle
from perun.io.text_report import textReport

log = logging.getLogger("perun")

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

    Parameters
    ----------
    output_path : Path
        Output Path
    dataNode : DataNode
        DataNode Object
    format : IOFormat
        Selected output format
    mr_id : Optional[str], optional
        Run id to extract from DataNode, by default None

    Raises
    ------
    Exception
        If the data has not been processed.
    """
    if not dataNode.processed:
        log.error("Data has not been processed before import. Proceed with caution.")
        raise Exception("DataNode needs to be processed before it can be exported.")

    if not output_path.exists():
        log.warning("Output directory does not exist. Creating it.")
        output_path.mkdir(parents=True)

    if not mr_id and (
        format == IOFormat.BENCH or format == IOFormat.TEXT or format == IOFormat.CSV
    ):
        log.info("No run ID provided, using last executed run to generate output")
        last_dt = datetime.min
        for node in dataNode.nodes.values():
            exec_dt = datetime.fromisoformat(node.metadata["execution_dt"])
            if exec_dt > last_dt:
                last_dt = exec_dt
                mr_id = node.id

    reportStr: Union[str, bytes]
    if format == IOFormat.JSON:
        fileType = "w"
        output_path = output_path / f"{dataNode.id}.{format.suffix}"

        if output_path.exists() and output_path.is_file():
            log.info(f"Overwriting existing file {output_path}")

        reportStr = exportJson(dataNode)
        with open(output_path, fileType) as file:
            file.write(reportStr)

    elif format == IOFormat.HDF5:
        output_path = output_path / f"{dataNode.id}.{format.suffix}"
        if output_path.exists() and output_path.is_file():
            log.info(f"Overwriting existing file {output_path}")

        exportHDF5(output_path, dataNode)

    elif format == IOFormat.PICKLE:
        fileType = "wb"

        output_path = output_path / f"{dataNode.id}.{format.suffix}"

        if output_path.exists() and output_path.is_file():
            log.info(f"Overwriting existing file {output_path}")

        reportStr = exportPickle(dataNode)
        with open(output_path, fileType) as file:
            file.write(reportStr)

    elif format == IOFormat.CSV:
        output_path = output_path / f"{dataNode.id}_{mr_id}.{format.suffix}"

        if output_path.exists() and output_path.is_file():
            log.info(f"Overwriting existing file {output_path}")

        exportCSV(output_path, dataNode, mr_id)  # type: ignore
    elif format == IOFormat.BENCH:
        fileType = "w"
        output_path = output_path / f"{dataNode.id}_{mr_id}.{format.suffix}"

        if output_path.exists() and output_path.is_file():
            log.info(f"Overwriting existing file {output_path}")

        reportStr = exportBench(dataNode, mr_id)  # type: ignore
        with open(output_path, fileType) as file:
            file.write(reportStr)

    elif format == IOFormat.TEXT:
        fileType = "w"
        output_path = output_path / f"{dataNode.id}_{mr_id}.{format.suffix}"

        if output_path.exists() and output_path.is_file():
            log.info(f"Overwriting existing file {output_path}")

        reportStr = textReport(dataNode, mr_id)  # type: ignore
        with open(output_path, fileType, encoding="utf-8") as file:
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
