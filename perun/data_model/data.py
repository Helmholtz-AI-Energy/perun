"""Storage Module."""
import dataclasses
import enum
import time
from typing import Any, Dict, List, Optional, Union

import numpy as np

from perun import log
from perun.data_model.measurement_type import MetricMetaData
from perun.data_model.sensor import DeviceType


class NodeType(enum.Enum):
    """DataNode type enum."""

    APP = enum.auto()
    MULTI_RUN = enum.auto()
    RUN = enum.auto()
    NODE = enum.auto()
    DEVICE_GROUP = enum.auto()
    SENSOR = enum.auto()


class MetricType(str, enum.Enum):
    """Metric Type enum."""

    RUNTIME = "runtime"
    POWER = "power"
    CPU_POWER = "cpu_power"
    GPU_POWER = "gpu_power"
    DRAM_POWER = "dram_power"
    OTHER_POWER = "other_power"
    CPU_UTIL = "cpu_util"
    GPU_UTIL = "gpu_util"
    MEM_UTIL = "mem_util"
    NET_READ = "net_read"
    NET_WRITE = "net_write"
    DISK_READ = "disk_read"
    DISK_WRITE = "disk_write"
    ENERGY = "energy"
    CPU_ENERGY = "cpu_energy"
    GPU_ENERGY = "gpu_energy"
    DRAM_ENERGY = "dram_energy"
    OTHER_ENERGY = "other_energy"


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
    def fromDict(cls, metricDict: Dict):
        """Create RawData object from a dictionary."""
        return cls(
            MetricType(metricDict["type"]),
            np.float32(metricDict["value"]),
            MetricMetaData.fromDict(metricDict["metric_md"]),
            AggregateType(metricDict["agg"]),
        )

    def copy(self):
        """Create copy metric object.

        Returns
        -------
        _type_
            Copy of object.
        """
        return Metric(
            MetricType(self.type.value),
            self.value.copy(),
            self.metric_md.copy(),
            AggregateType(self.agg.value),
        )


class LocalRegions:
    """Stores local region data while an application is being monitored."""

    def __init__(self) -> None:
        self._regions: Dict[str, List[int]] = {}

    def addEvent(self, region_name: str) -> None:
        """Mark a new event for the named region.

        Parameters
        ----------
        region_name : str
            Region to mark the event from.
        """
        if region_name not in self._regions:
            self._regions[region_name] = []

        self._regions[region_name].append(time.time_ns())


class Regions:
    """Stores region data from all MPI ranks.

    For each marked region (decorated function), an numpy array with timestamps indicating function starts and ends.
    """

    def __init__(self) -> None:
        self._regions: Dict[str, Dict[int, np.ndarray]] = {}

    def getRegion(self, region_name: str) -> Dict[int, np.ndarray]:
        """Get data from a named region.

        Parameters
        ----------
        region_name : str
            Region id.

        Returns
        -------
        Dict[int, np.ndarray]
            Region data from all MPI ranks.
        """
        return self._regions[region_name]

    def getRegionFromRank(self, region_name: str, rank: int) -> np.ndarray:
        """Obtain region data from a particular MPI rank.

        Parameters
        ----------
        region_name : str
            Region id.
        rank : int
            MPI rank.

        Returns
        -------
        np.ndarray
            Numpy array with all marked event timestamps.
        """
        return self._regions[region_name][rank]

    def toDict(self) -> Dict[str, Dict[int, np.ndarray]]:
        """Convert regions to a python dictionary.

        Returns
        -------
        Dict[str, Dict[int, np.ndarray]]
            Dictionary with region data.
        """
        return self._regions

    @classmethod
    def fromLocalRegions(cls, local_regions: List[LocalRegions], start_time: int):
        """Create a Regions object from a list of local regions.

        Parameters
        ----------
        local_regions : List[LocalRegions]
            Local region objects collected from multiple MPI ranks.
        """
        regionObj = cls()
        for rank, local_region in enumerate(local_regions):
            for region_name, region in local_region._regions.items():
                if region_name not in regionObj._regions:
                    regionObj._regions[region_name] = {}

                t_s = np.array(region)
                t_s -= start_time
                t_s = t_s.astype("float32")
                t_s *= 1e-9

                regionObj._regions[region_name][rank] = t_s
        return regionObj

    @classmethod
    def fromDict(cls, regions: Dict[str, Dict[int, np.ndarray]]):
        """Create Regions object from a dictionary.

        Parameters
        ----------
        regions : Dict[str, Dict[int, np.ndarray]]
            Regions dictionary.

        Returns
        -------
        Regions
            Regions object.
        """
        regionObj = cls()
        regionObj._regions = regions
        return regionObj


@dataclasses.dataclass
class Stats:
    """Collects statistics based on multiple metrics of the same type."""

    type: MetricType
    metric_md: MetricMetaData
    sum: np.number
    mean: np.number
    std: np.number
    max: np.number
    min: np.number

    @classmethod
    def fromMetrics(cls, metrics: List[Metric]):
        """Create stats object from list of metrics with the same type.

        Parameters
        ----------
        metrics : List[Metric]
            List of metrics with  the same type.

        Returns
        -------
        _type_
            Stats object.

        Raises
        ------
        Exception
            If metrics are not from the same type.
        """
        type = metrics[0].type
        metric_md = metrics[0].metric_md

        for m in metrics:
            if m.type != type:
                log.error("Metrics given to Stats class do not match")
                raise Exception("Metrics type don't match. Invalid Stats")

        values = np.array([metric.value for metric in metrics])
        sum = values.sum()
        mean = values.mean()
        std = values.std()
        max = values.max()
        min = values.min()
        return cls(type, metric_md, sum, mean, std, max, min)

    @property
    def value(self):
        """Value property (mean).

        For compatibility with Metric dataclass.

        Returns
        -------
        _type_
            Return the mean value of the stats object.
        """
        return self.mean

    @classmethod
    def fromDict(cls, statsDict: Dict):
        """Stats constructor from a dictionory."""
        return cls(
            MetricType(statsDict["type"]),
            MetricMetaData.fromDict(statsDict["metric_md"]),
            statsDict["min"],
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
    def fromDict(cls, rawDataDict: Dict):
        """Create RawData object from a dictionary.

        Parameters
        ----------
        rawDataDict : Dict
            Dictionary with same keys as RawData object.

        Returns
        -------
        _type_
            RawData object.
        """
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
        nodes: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[MetricType, Union[Metric, Stats]]] = None,
        deviceType: Optional[DeviceType] = None,
        raw_data: Optional[RawData] = None,
        regions: Optional[Regions] = None,
        processed: bool = False,
    ) -> None:
        """Perun DataNode.

        Parameters
        ----------
        id : str
            Node id.
        type : NodeType
            Node type.
        metadata : Dict
            Node metadata.
        nodes : Optional[Dict[str, Any]], optional
            Children nodes, by default None
        metrics : Optional[Dict[MetricType, Union[Metric, Stats]]], optional
            Node metrics, by default None
        deviceType : Optional[DeviceType], optional
            Node device type, only relevant for leaf nodes, by default None
        raw_data : Optional[RawData], optional
            Raw data object, only relevant for leaf nodes, by default None
        processed : bool, optional
            Marks if the node has been processed, by default False
        """
        self.id = id
        self.type = type
        self.metadata: Dict[str, Any] = metadata
        self.nodes: Dict[str, Any] = nodes if nodes else {}
        self.metrics: Dict[MetricType, Union[Metric, Stats]] = (
            metrics if metrics else {}
        )
        self.deviceType: Optional[DeviceType] = deviceType
        self.raw_data: Optional[RawData] = raw_data
        self.regions: Optional[Regions] = regions
        self.processed = processed

    def toDict(self, include_raw_data: bool = True) -> Dict:
        """Transform object to dictionary."""
        resultsDict = {
            "id": self.id,
            "type": self.type.value,
            "metadata": self.metadata,
            "metrics": {
                type.value: dataclasses.asdict(metric)
                for type, metric in self.metrics.items()
            },
            "regions": self.regions.toDict() if self.regions else None,
            "deviceType": self.deviceType,
            "processed": self.processed,
        }
        resultsDict["nodes"] = (
            {key: value.toDict(include_raw_data) for key, value in self.nodes.items()},
        )

        if include_raw_data and self.raw_data:
            resultsDict["raw_data"] = dataclasses.asdict(self.raw_data)

        return resultsDict

    @classmethod
    def fromDict(cls, resultsDict: Dict):
        """Create dataNode from python dictionary.

        Parameters
        ----------
        resultsDict : Dict
            Dictionary with data node attributes.

        Returns
        -------
        _type_
            DataNode object.
        """
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

        if "regions" in resultsDict:
            newResults.regions = Regions.fromDict(resultsDict["regions"])

        return newResults
