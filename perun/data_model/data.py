"""Storage Module."""

import dataclasses
import enum
import logging
import time
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Union

import numpy as np

from perun.data_model.measurement_type import MetricMetaData
from perun.data_model.sensor import DeviceType

log = logging.getLogger("perun")


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
    OTHER_UTIL = "other_util"
    DRAM_MEM = "dram_mem"
    GPU_MEM = "gpu_mem"
    NET_READ = "net_read"
    NET_WRITE = "net_write"
    DISK_READ = "disk_read"
    DISK_WRITE = "disk_write"
    ENERGY = "energy"
    CPU_ENERGY = "cpu_energy"
    GPU_ENERGY = "gpu_energy"
    DRAM_ENERGY = "dram_energy"
    OTHER_ENERGY = "other_energy"
    OTHER_MEM = "other_memory"
    CPU_CLOCK = "cpu_clock"
    GPU_CLOCK = "gpu_clock"
    N_RUNS = "n_runs"
    MONEY = "money"
    CO2 = "co2"

    def __str__(self):
        """Return string representation of MetricType."""
        return self.value

    def __repr__(self):
        """Return string representation of MetricType."""
        return self.value

    def fromString(self, value: str):
        """Create MetricType from string.

        Parameters
        ----------
        value : str
            MetricType value.

        Returns
        -------
        MetricType
            MetricType object.
        """
        return MetricType(value)


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
    alt_values: Optional[np.ndarray] = None
    alt_v_md: Optional[MetricMetaData] = None

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
        alt_v_md = (
            MetricMetaData.fromDict(rawDataDict["alt_v_md"])
            if "alt_v_md" in rawDataDict
            else None
        )
        return cls(
            timesteps=np.array(rawDataDict["timesteps"], dtype=t_md.dtype),
            values=np.array(rawDataDict["values"], dtype=t_md.dtype),
            alt_values=(
                np.array(rawDataDict["alt_values"], dtype=alt_v_md.dtype)  # type: ignore
                if "alt_values" in rawDataDict
                else None
            ),
            t_md=t_md,
            v_md=v_md,
            alt_v_md=alt_v_md,
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

    def isEmpty(self) -> bool:
        """Check if there are any regions marked.

        Returns
        -------
        bool
            True if there are no regions marked.
        """
        return len(self._regions.keys()) == 0

    def __str__(self) -> str:
        """Return string representation of LocalRegions object."""
        return str(self._regions)


@dataclasses.dataclass
class Region:
    """Stores region data from all MPI ranks.

    For each marked region (decorated function), an numpy array with timestamps indicating function starts and ends.
    """

    id: str = ""
    raw_data: Dict[int, np.ndarray] = dataclasses.field(default_factory=dict)
    runs_per_rank: Optional[Stats] = None
    metrics: Dict[MetricType, Stats] = dataclasses.field(default_factory=dict)
    processed: bool = False

    def toDict(self) -> Dict[str, Any]:
        """Convert regions to a python dictionary.

        Returns
        -------
        Dict[str, Dict[int, np.ndarray]]
            Dictionary with region data.
        """
        result: Dict[str, Any] = {
            "id": self.id,
            "raw_data": self.raw_data,
        }

        result["runs_per_rank"] = (
            asdict(self.runs_per_rank) if self.runs_per_rank else None
        )
        result["metrics"] = [asdict(metric) for metric in self.metrics.values()]

        return result

    @classmethod
    def fromDict(cls, regionDictionary: Dict[str, Any]):
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
        regionObj = Region()
        regionObj.id = regionDictionary["id"]
        regionObj.raw_data = regionDictionary["raw_data"]
        regionObj.processed = regionDictionary["processed"]
        if regionObj.processed:
            regionObj.metrics = {
                MetricType(metric["type"]): Stats.fromDict(metric)
                for metric in regionDictionary["metrics"]
            }
        return regionObj


class DataNode:
    """Recursive data structure that contains all the information of a monitored application."""

    def __init__(
        self,
        id: str,
        type: NodeType,
        metadata: Dict = {},
        nodes: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[MetricType, Union[Metric, Stats]]] = None,
        deviceType: Optional[DeviceType] = None,
        raw_data: Optional[RawData] = None,
        regions: Optional[Dict[str, Region]] = None,
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
        self.regions: Optional[Dict[str, Region]] = regions
        self.processed = processed

    def addRegionData(self, localRegions: List[LocalRegions], start_time: int):
        """Add region information to to data node.

        Parameters
        ----------
        localRegions : List[LocalRegions]
            Gathered local regions from all MPI ranks
        start_time : int
            'Official' start time of the run.
        """
        self.regions = {}
        log.debug(f"Local regions: {localRegions}")
        for rank, l_region in enumerate(localRegions):
            if not l_region.isEmpty():
                for region_name, data in l_region._regions.items():
                    if region_name not in self.regions:
                        r = Region()
                        r.id = region_name
                        self.regions[region_name] = r

                    t_s = np.array(data)
                    t_s -= start_time
                    t_s = t_s.astype("float32")
                    t_s *= 1e-9
                    self.regions[region_name].raw_data[rank] = t_s

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
            "regions": (
                {
                    region_name: region.toDict()
                    for region_name, region in self.regions.items()
                }
                if self.regions
                else None
            ),
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
            newResults.regions = {
                region_name: Region.fromDict(region_dict)
                for region_name, region_dict in resultsDict["regions"].items()
            }

        return newResults
