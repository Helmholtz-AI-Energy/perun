"""Storage Module."""
import dataclasses
import enum
from typing import Any, Dict, List, Optional

import numpy as np
from typing_extensions import Self

from perun.data_model.measurement_type import MetricMetaData
from perun.data_model.sensor import DeviceType


class NodeType(enum.Enum):
    """DataNode type enum."""

    RUN = "run"
    NODE = "node"
    DEVICE_GROUP = "device group"
    SENSOR = "sensor"


class MetricType(enum.Enum):
    """Metric Type enum."""

    RUNTIME = "runtime"
    ENERGY = "energy"
    POWER = "power"
    CPU_UTIL = "cpu util"
    GPU_UTIL = "gpu util"
    MEM_UTIL = "mem util"
    NET_READ = "net read"
    NET_WRITE = "net write"
    DISK_READ = "disk read"
    DISK_WRITE = "disk write"


class AggregateType(enum.Enum):
    """Types of data aggregation."""

    SUM = "sum"
    MEAN = "mean"
    MAX = "max"
    MIN = "min"


@dataclasses.dataclass
class Metric:
    """Struct with resulting metrics and the metadata."""

    type: MetricType
    value: np.number
    metric_md: MetricMetaData
    agg: AggregateType

    @classmethod
    def fromDict(cls, metricDict: Dict) -> Self:
        """Create RawData object from a dictionary."""
        return cls(
            MetricType(metricDict["type"]),
            np.float32(metricDict["value"]),
            MetricMetaData.fromDict(metricDict["metric_md"]),
            AggregateType(metricDict["agg"]),
        )


@dataclasses.dataclass
class RawData:
    """Contains timesteps and recorded values from sensors, including information on the values."""

    timesteps: np.ndarray
    values: np.ndarray
    t_md: MetricMetaData
    v_md: MetricMetaData

    @classmethod
    def fromDict(cls, rawDataDict: Dict) -> Self:
        """Create RawData object from a dictionary."""
        t_md = MetricMetaData.fromDict(rawDataDict["t_md"])
        v_md = MetricMetaData.fromDict(rawDataDict["v_md"])
        return cls(
            np.array(rawDataDict["timesteps"], dtype=t_md.dtype),
            np.array(rawDataDict["values"], dtype=t_md.dtype),
            t_md,
            v_md,
        )


class DataNode:
    """Recursive data structure that contains all the information of a monitored application."""

    def __init__(
        self,
        id: str,
        type: NodeType,
        metadata: Dict,
        nodes: Optional[Dict[str, Self]] = None,
        metrics: Optional[List[Metric]] = None,
        deviceType: Optional[DeviceType] = None,
        raw_data: Optional[RawData] = None,
        processed: bool = False,
    ) -> None:
        """DataNode.

        Args:
            id (str): String identifier
            type (NodeType): Type of Node
            metadata (Dict): Metadata
            nodes (Dict[str, Self], optional): Child DataNodes. Defaults to {}.
            raw_data (Optional[RawData], optional): If sensor, contains raw sensor values. Defaults to None.
        """
        self.id = id
        self.type = type
        self.metadata: Dict[str, Any] = metadata
        self.nodes: Dict[str, Self] = nodes if nodes else {}
        self.metrics: List[Metric] = metrics if metrics else []
        self.deviceType: Optional[DeviceType] = deviceType
        self.raw_data: Optional[RawData] = raw_data
        self.processed = processed

    def toDict(self, include_raw_data: bool = False) -> Dict:
        """Transform object to dictionary."""
        resultsDict = {
            "id": self.id,
            "metadata": self.metadata,
            "nodes": {
                key: value.toDict(include_raw_data) for key, value in self.nodes.items()
            },
            "metrics": [dataclasses.asdict(metric) for metric in self.metrics],
            "processed": self.processed,
        }
        if include_raw_data and self.raw_data:
            resultsDict["raw_data"] = dataclasses.asdict(self.raw_data)

        return resultsDict

    @classmethod
    def fromDict(cls, resultsDict: Dict) -> Self:
        """Build object from dictionary."""
        newResults = cls(
            id=resultsDict["id"],
            type=NodeType(resultsDict["type"]),
            metadata=resultsDict["metadata"],
            nodes={
                key: DataNode.fromDict(node)
                for key, node in resultsDict["nodes"].items()
            },
            processed=resultsDict["processed"],
        )
        if "deviceType" in resultsDict:
            newResults.deviceType = DeviceType(resultsDict["deviceType"])

        if "raw_data" in resultsDict:
            newResults.metrics = [
                Metric.fromDict(metricDict) for metricDict in resultsDict["metrics"]
            ]
        return newResults
