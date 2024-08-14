"""HDF5 IO module."""

from pathlib import Path
from typing import Dict, Union

import h5py
import numpy as np

from perun.data_model.data import (
    AggregateType,
    DataNode,
    Metric,
    MetricMetaData,
    MetricType,
    NodeType,
    RawData,
    Region,
    Stats,
)
from perun.data_model.measurement_type import Magnitude, Unit
from perun.data_model.sensor import DeviceType


def exportHDF5(filePath: Path, dataNode: DataNode):
    """Export perun data nodes to an HDF5 file.

    Parameters
    ----------
    filePath : Path
        Output path
    dataNode : DataNode
        Root of data node tree.
    """
    h5_file = h5py.File(filePath, "w")
    _addNode(h5_file, dataNode)
    h5_file.close()


def importHDF5(filePath: Path) -> DataNode:
    """Import DataNode from HDF5 format.

    Parameters
    ----------
    filePath : Path
        HDF5 file path.

    Returns
    -------
    DataNode
        Perun data node.

    Raises
    ------
    ValueError
        Incompatible HDF5 file.
    """
    h5_file = h5py.File(filePath, "r")
    rootEntries = list(h5_file.keys())
    if len(rootEntries) != 1:
        raise ValueError("Invalid number of entries in hdf5 file.")

    key = list(h5_file.keys())[0]
    rootGroup = h5_file[key]
    if isinstance(rootGroup, h5py.Group):
        return _readNode(rootGroup)
    else:
        raise ValueError("Invalid root level entry.")


def _addNode(h5group: h5py.Group, dataNode: DataNode):
    """Write node into hdf5 file."""
    group = h5group.create_group(dataNode.id)
    group.attrs["type"] = dataNode.type.value

    for key, value in dataNode.metadata.items():
        group.attrs[key] = value

    if dataNode.deviceType is not None:
        group.attrs["device_type"] = dataNode.deviceType.value

    metricGroup = group.create_group("metrics")
    for metric in dataNode.metrics.values():
        _addMetric(metricGroup, metric)

    nodesGroup = group.create_group("nodes")
    for node in dataNode.nodes.values():
        _addNode(nodesGroup, node)

    if dataNode.raw_data is not None:
        _addRawData(group, dataNode.raw_data)

    if dataNode.regions is not None:
        _addRegions(group, dataNode.regions)


def _readNode(group: h5py.Group) -> DataNode:
    """Read node from hdf5 file."""
    id = group.name.split("/")[-1]  # type: ignore
    type = NodeType(group.attrs["type"])
    device_type = (
        DeviceType(group.attrs["device_type"]) if "device_type" in group.attrs else None
    )
    metadata = {}
    for key, value in group.attrs.items():
        if key not in ["type", "device_type"]:
            metadata[key] = value

    nodes = {}
    for key, value in group["nodes"].items():  # type: ignore
        node = _readNode(value)  # type: ignore
        nodes[node.id] = node

    metrics = {}
    for key, value in group["metrics"].items():  # type: ignore
        metric = _readMetric(value)  # type: ignore
        metrics[metric.type] = metric

    raw_data = _readRawData(group["raw_data"]) if "raw_data" in group else None  # type: ignore
    regions = _readRegions(group["regions"]) if "regions" in group else None  # type: ignore

    return DataNode(
        id=id,
        type=type,
        metadata=metadata,
        nodes=nodes,
        metrics=metrics,
        deviceType=device_type,
        raw_data=raw_data,
        regions=regions,
        processed=True,
    )


def _addMetric(h5Group: h5py.Group, metric: Union[Metric, Stats]):
    """Write metric into hdf5 file."""
    metricGroup = h5Group.create_group(metric.type.name)

    metadata = metric.metric_md
    _addMetricMetadata(metricGroup, metadata)

    metricGroup.attrs["type"] = metric.type.value
    if isinstance(metric, Metric):
        metricGroup.attrs["agg_type"] = metric.agg.value
        metricGroup.attrs.create("value", metric.value, dtype=metadata.dtype)
    else:
        metricGroup.attrs.create("sum", metric.sum, dtype=metadata.dtype)
        metricGroup.attrs.create("mean", metric.mean, dtype=metadata.dtype)
        metricGroup.attrs.create("min", metric.min, dtype=metadata.dtype)
        metricGroup.attrs.create("max", metric.max, dtype=metadata.dtype)
        metricGroup.attrs.create("std", metric.std, dtype=metadata.dtype)


def _readMetric(group: h5py.Group) -> Union[Metric, Stats]:
    """Read metric from hdf5 file."""
    metric_md = _readMetricMetadata(group)
    if "value" in group.attrs:
        return Metric(
            type=MetricType(group.attrs["type"]),
            value=group.attrs["value"],  # type: ignore
            metric_md=metric_md,
            agg=AggregateType(group.attrs["agg_type"]),
        )
    else:
        return Stats(
            type=MetricType(group.attrs["type"]),
            metric_md=metric_md,
            sum=group.attrs["sum"],  # type: ignore
            mean=group.attrs["mean"],  # type: ignore
            std=group.attrs["std"],  # type: ignore
            min=group.attrs["min"],  # type: ignore
            max=group.attrs["max"],  # type: ignore
        )


def _addMetricMetadata(
    group: Union[h5py.Group, h5py.Dataset], metadata: MetricMetaData
):
    """Write metric metadata into hdf5 file."""
    group.attrs["unit"] = metadata.unit.value
    group.attrs["mag"] = metadata.mag.value
    group.attrs["dtype"] = metadata.dtype.name
    group.attrs.create("valid_min", metadata.min, dtype=metadata.dtype)
    group.attrs.create("valid_max", metadata.max, dtype=metadata.dtype)
    group.attrs.create("fill", metadata.fill, dtype=metadata.dtype)


def _readMetricMetadata(group: Union[h5py.Group, h5py.Dataset]) -> MetricMetaData:
    """Read metric metadata form into hdf5 file."""
    dtype = np.dtype(group.attrs["dtype"])
    return MetricMetaData(
        unit=Unit(group.attrs["unit"]),
        mag=Magnitude(group.attrs["mag"]),  # type: ignore
        dtype=dtype,
        min=group.attrs["valid_min"],  # type: ignore
        max=group.attrs["valid_max"],  # type: ignore
        fill=group.attrs["fill"],  # type: ignore
    )


def _addRawData(h5Group: h5py.Group, rawData: RawData):
    """Write raw data into hdf5 file."""
    rawDataGroup = h5Group.create_group("raw_data")

    timestep_ds = rawDataGroup.create_dataset("timesteps", data=rawData.timesteps)
    _addMetricMetadata(timestep_ds, rawData.t_md)

    values_ds = rawDataGroup.create_dataset("values", data=rawData.values)
    _addMetricMetadata(values_ds, rawData.v_md)

    if rawData.alt_values is not None:
        alt_values_ds = rawDataGroup.create_dataset(
            "alt_values", data=rawData.alt_values
        )
        _addMetricMetadata(alt_values_ds, rawData.alt_v_md)  # type: ignore


def _readRawData(group: h5py.Group) -> RawData:
    """Read raw data from into hdf5."""
    timesteps = group["timesteps"][:]  # type: ignore
    values = group["values"][:]  # type: ignore
    t_md = _readMetricMetadata(group["timesteps"])  # type: ignore
    v_md = _readMetricMetadata(group["values"])  # type: ignore

    alt_values = group["alt_values"][:] if "alt_values" in group else None  # type: ignore
    alt_v_md = (
        _readMetricMetadata(group["alt_values"]) if alt_values is not None else None
    )  # type: ignore
    return RawData(
        timesteps=timesteps,  # type: ignore
        values=values,  # type: ignore
        alt_values=alt_values,
        t_md=t_md,
        v_md=v_md,
        alt_v_md=alt_v_md,
    )


def _addRegions(h5Group: h5py.Group, regions: Dict[str, Region]):
    regions_group: h5py.Group = h5Group.create_group("regions")
    for region in regions.values():
        _addRegion(regions_group, region)


def _addRegion(h5Group: h5py.Group, region: Region):
    region_group = h5Group.create_group(region.id)
    region_group.attrs["id"] = region.id
    region_group.attrs["processed"] = region.processed

    region_metrics = region_group.create_group("metrics")
    _addMetric(region_group, region.runs_per_rank)  # type: ignore
    for metricType, stat in region.metrics.items():
        _addMetric(region_metrics, stat)
    raw_data_group = region_group.create_group("raw_data")
    for rank, data in region.raw_data.items():
        raw_data_group.create_dataset(str(rank), data=data)


def _readRegions(group: h5py.Group) -> Dict[str, Region]:
    regionsDict: Dict[str, Region] = {}
    for key, region_group in group.items():
        regionsDict[key] = _readRegion(region_group)
    return regionsDict


def _readRegion(group: h5py.Group) -> Region:
    regionObj = Region()
    regionObj.id = group.attrs["id"]  # type: ignore
    regionObj.processed = group.attrs["processed"]  # type: ignore

    for metric_group in group["metrics"].values():  # type: ignore
        stat: Stats = _readMetric(metric_group)  # type: ignore
        regionObj.metrics[stat.type] = stat
    regionObj.runs_per_rank = _readMetric(group["N_RUNS"])  # type: ignore

    raw_data_group = group["raw_data"]
    regionObj.raw_data = {}
    for key, data in raw_data_group.items():  # type: ignore
        regionObj.raw_data[int(key)] = data[:]

    return regionObj
