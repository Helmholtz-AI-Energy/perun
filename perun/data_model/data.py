"""Storage Module."""
import dataclasses
import enum
from typing import Any, Dict, List, Optional, Union

import numpy as np
from typing_extensions import Self

from perun import log
from perun.data_model.measurement_type import MetricMetaData
from perun.data_model.sensor import DeviceType


class NodeType(enum.Enum):
    """DataNode type enum."""

    MULTI_RUN = enum.auto()
    RUN = enum.auto()
    NODE = enum.auto()
    DEVICE_GROUP = enum.auto()
    SENSOR = enum.auto()


class MetricType(str, enum.Enum):
    """Metric Type enum."""

    RUNTIME = "runtime"
    POWER = "power"
    CPU_UTIL = "cpu_util"
    GPU_UTIL = "gpu_util"
    MEM_UTIL = "mem_util"
    NET_READ = "net_read"
    NET_WRITE = "net_write"
    DISK_READ = "disk_read"
    DISK_WRITE = "disk_write"
    ENERGY = "energy"


class AggregateType(str, enum.Enum):
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
class Stats:
    """Collects statistics based on multiple metrics of the same type."""

    type: MetricType
    metric_md: MetricMetaData
    mean: np.number
    std: np.number
    max: np.number
    min: np.number

    @classmethod
    def fromMetrics(cls, metrics: List[Metric]) -> Self:
        """Create a stats object based on the metric's values."""
        type = metrics[0].type
        metric_md = metrics[0].metric_md

        for m in metrics:
            if m.type != type:
                log.error("Metrics given to Stats class do not match")
                raise Exception("Metrics type don't match. Invalid Stats")

        values = np.array([metric.value for metric in metrics])
        mean = values.mean()
        std = values.std()
        max = values.max()
        min = values.min()
        return cls(type, metric_md, mean, std, max, min)

    @property
    def value(self):
        """
        Value property.

        For compatibility with Metric dataclass.
        """
        return self.mean

    @classmethod
    def fromDict(cls, statsDict: Dict) -> Self:
        """Stats constructor from a dictionory."""
        return cls(
            MetricType(statsDict["type"]),
            MetricMetaData.fromDict(statsDict["metric_md"]),
            statsDict["mean"],
            statsDict["std"],
            statsDict["max"],
            statsDict["min"],
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
        metrics: Optional[Dict[MetricType, Union[Metric, Stats]]] = None,
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
        self.metrics: Dict[MetricType, Union[Metric, Stats]] = (
            metrics if metrics else {}
        )
        self.deviceType: Optional[DeviceType] = deviceType
        self.raw_data: Optional[RawData] = raw_data
        self.processed = processed

    def toDict(
        self, depth: Optional[int] = None, include_raw_data: bool = False
    ) -> Dict:
        """Transform object to dictionary."""
        resultsDict = {
            "id": self.id,
            "type": self.type.value,
            "metadata": self.metadata,
            "metrics": {
                type.value: dataclasses.asdict(metric)
                for type, metric in self.metrics.items()
            },
            "deviceType": self.deviceType,
            "processed": self.processed,
        }
        if depth is None:
            resultsDict["nodes"] = (
                {
                    key: value.toDict(depth, include_raw_data)
                    for key, value in self.nodes.items()
                },
            )
        elif depth > 1:
            resultsDict["nodes"] = (
                {
                    key: value.toDict(depth - 1, include_raw_data)
                    for key, value in self.nodes.items()
                },
            )

        if include_raw_data and self.raw_data:
            resultsDict["raw_data"] = dataclasses.asdict(self.raw_data)

        return resultsDict

    @classmethod
    def fromDict(cls, resultsDict: Dict) -> Self:
        """Build object from dictionary."""
        type = NodeType(resultsDict["type"])
        newResults = cls(
            id=resultsDict["id"],
            type=type,
            metadata=resultsDict["metadata"],
            nodes={
                key: DataNode.fromDict(node)
                for key, node in resultsDict["nodes"].items()
            },
            processed=resultsDict["processed"],
        )
        if "deviceType" in resultsDict:
            newResults.deviceType = DeviceType(resultsDict["deviceType"])

        if "metrics" in resultsDict:
            if type == NodeType.MULTI_RUN:
                newResults.metrics = {
                    MetricType(type): Stats.fromDict(metricDict)
                    for type, metricDict in resultsDict["metrics"].items()
                }
            else:
                newResults.metrics = {
                    MetricType(type): Metric.fromDict(metricDict)
                    for type, metricDict in resultsDict["metrics"].items()
                }
        if "raw_data" in resultsDict:
            newResults.raw_data = RawData.fromDict(resultsDict["raw_data"])

        return newResults
