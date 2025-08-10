"""HDF5 IO module."""

import logging
from pathlib import Path
from typing import Dict, Optional, Union

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

log = logging.getLogger(__name__)


def exportHDF5(filePath: Path, dataNode: DataNode) -> None:
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


def _addNode(h5group: h5py.Group, dataNode: DataNode) -> None:
    """Write node into hdf5 file."""
    group = h5group.create_group(dataNode.id)
    group.attrs["type"] = dataNode.type.value

    for key, value in dataNode.metadata.items():
        log.debug(f"Adding metadata {key}={value} to node {dataNode.id}")
        group.attrs[key] = str(value)

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
    id = group.name.split("/")[-1]
    type = NodeType(group.attrs["type"])
    device_type = (
        DeviceType(group.attrs["device_type"]) if "device_type" in group.attrs else None
    )
    metadata = {}
    for key, value in group.attrs.items():
        if key not in ["type", "device_type"]:
            metadata[key] = value

    nodes = {}
    for key, value in group["nodes"].items():
        node = _readNode(value)
        nodes[node.id] = node

    metrics = {}
    for key, value in group["metrics"].items():
        metric = _readMetric(value)
        metrics[metric.type] = metric

    raw_data = _readRawData(group["raw_data"]) if "raw_data" in group else None
    regions = _readRegions(group["regions"]) if "regions" in group else None

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


def _addMetric(h5Group: h5py.Group, metric: Union[Metric, Stats]) -> None:
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
            value=group.attrs["value"],
            metric_md=metric_md,
            agg=AggregateType(group.attrs["agg_type"]),
        )
    else:
        return Stats(
            type=MetricType(group.attrs["type"]),
            metric_md=metric_md,
            sum=group.attrs["sum"],
            mean=group.attrs["mean"],
            std=group.attrs["std"],
            min=group.attrs["min"],
            max=group.attrs["max"],
        )


def _addMetricMetadata(
    group: Union[h5py.Group, h5py.Dataset], metadata: MetricMetaData
) -> None:
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
        min=group.attrs["valid_min"],
        max=group.attrs["valid_max"],
        fill=group.attrs["fill"],
    )


def _addRawData(h5Group: h5py.Group, rawData: RawData) -> None:
    """Write raw data into hdf5 file."""
    rawDataGroup = h5Group.create_group("raw_data")

    timestep_ds = rawDataGroup.create_dataset("timesteps", data=rawData.timesteps)
    _addMetricMetadata(timestep_ds, rawData.t_md)

    values_ds = rawDataGroup.create_dataset("values", data=rawData.values)
    _addMetricMetadata(values_ds, rawData.v_md)

    if rawData.alt_values is not None and rawData.alt_v_md is not None:
        alt_values_ds = rawDataGroup.create_dataset(
            "alt_values", data=rawData.alt_values
        )
        _addMetricMetadata(alt_values_ds, rawData.alt_v_md)


def _readRawData(group: h5py.Group) -> RawData:
    """Read raw data from into hdf5."""
    timesteps_ds: h5py.Dataset = group["timesteps"]
    values_ds: h5py.Dataset = group["values"]
    t_md = _readMetricMetadata(timesteps_ds)
    v_md = _readMetricMetadata(values_ds)

    alt_values_ds: Optional[h5py.Dataset] = (
        group["alt_values"] if "alt_values" in group else None
    )
    alt_v_md: Optional[MetricMetaData] = (
        _readMetricMetadata(alt_values_ds) if alt_values_ds is not None else None
    )
    return RawData(
        timesteps=timesteps_ds[:],
        values=values_ds[:],
        alt_values=alt_values_ds[:] if alt_values_ds else None,
        t_md=t_md,
        v_md=v_md,
        alt_v_md=alt_v_md,
    )


def _addRegions(h5Group: h5py.Group, regions: Dict[str, Region]) -> None:
    regions_group: h5py.Group = h5Group.create_group("regions")
    for region in regions.values():
        _addRegion(regions_group, region)


def _addRegion(h5Group: h5py.Group, region: Region) -> None:
    region_group = h5Group.create_group(region.id)
    region_group.attrs["id"] = region.id
    region_group.attrs["processed"] = region.processed

    region_metrics = region_group.create_group("metrics")
    _addMetric(region_group, region.runs_per_rank)  # type: ignore[arg-type]
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
    regionObj.id = group.attrs["id"]
    regionObj.processed = group.attrs["processed"]

    for metric_group in group["metrics"].values():
        stat: Stats = _readMetric(metric_group)  # type: ignore[assignment]
        regionObj.metrics[stat.type] = stat
    regionObj.runs_per_rank = _readMetric(group["N_RUNS"])  # type: ignore[assignment]

    raw_data_group = group["raw_data"]
    regionObj.raw_data = {}
    for key, data in raw_data_group.items():
        regionObj.raw_data[int(key)] = data[:]

    return regionObj
