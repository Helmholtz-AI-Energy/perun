"""HDF5 IO module."""
from pathlib import Path
from typing import Union

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
    Stats,
)
from perun.data_model.measurement_type import Magnitude, Unit
from perun.data_model.sensor import DeviceType


def exportHDF5(filePath: Path, dataNode: DataNode):
    """Export perun data nodes to an HDF5 file.

    Args:
        filePath (Path): Output path.
        dataNode (DataNode): DataNode.
    """
    h5_file = h5py.File(filePath, "a")
    _addNode(h5_file, dataNode)
    h5_file.close()


def importHDF5(filePath: Path) -> DataNode:
    """Import HDF5 created by perun.

    Args:
        filePath (Path): File path.

    Raises:
        ValueError: Incompatible hdf5 file.

    Returns:
        DataNode: Recoverd perun DataNode
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
    for metricId, metric in dataNode.metrics.items():
        _addMetric(metricGroup, metric)

    nodesGroup = group.create_group("nodes")
    for nodeId, node in dataNode.nodes.items():
        _addNode(nodesGroup, node)

    if dataNode.raw_data is not None:
        _addRawData(group, dataNode.raw_data)


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

    return DataNode(
        id=id,
        type=type,
        metadata=metadata,
        nodes=nodes,
        metrics=metrics,
        deviceType=device_type,
        raw_data=raw_data,
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
        mag=Magnitude(group.attrs["mag"]),
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


def _readRawData(group: h5py.Group) -> RawData:
    """Read raw data from into hdf5."""
    timesteps = group["timesteps"][:]  # type: ignore
    values = group["values"][:]  # type: ignore
    t_md = _readMetricMetadata(group["timesteps"])  # type: ignore
    v_md = _readMetricMetadata(group["values"])  # type: ignore
    return RawData(
        timesteps=timesteps,  # type: ignore
        values=values,  # type: ignore
        t_md=t_md,
        v_md=v_md,
    )
