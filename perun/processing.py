"""Processing Module."""
import copy
import logging
from configparser import ConfigParser
from datetime import datetime
from itertools import chain
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from perun.data_model.data import (
    AggregateType,
    DataNode,
    Metric,
    MetricType,
    NodeType,
    RawData,
    Region,
    Stats,
)
from perun.data_model.measurement_type import Magnitude, MetricMetaData, Unit
from perun.data_model.sensor import DeviceType

log = logging.getLogger("perun")


def processEnergyData(
    raw_data: RawData,
    start: Optional[np.number] = None,
    end: Optional[np.number] = None,
) -> Tuple[Any, Any]:
    """Calculate energy and power from an accumulated energy vector. (SEE RAPL).

    Using the start and end parameters the results can be limited to certain areas of the application run.

    Parameters
    ----------
    raw_data : RawData
        Raw Data from sensor
    start : Optional[np.number], optional
        Start time of region, by default None
    end : Optional[np.number], optional
        End time of region, by default None

    Returns
    -------
    _type_
       Tuple with total energy in joules and avg power in watts.
    """
    runtime = raw_data.timesteps[-1]
    t_s = raw_data.timesteps.astype("float32")
    t_s *= raw_data.t_md.mag.value / Magnitude.ONE.value

    e_J = raw_data.values
    maxValue = raw_data.v_md.max
    dtype = raw_data.v_md.dtype.name

    if start and end:
        runtime = end - start
        index = np.all([t_s >= start, t_s <= end], axis=0)
        e_J = e_J[index]

    d_energy = e_J[1:] - e_J[:-1]

    if "uint" in dtype:
        idx = d_energy >= maxValue
        max_dtype = np.iinfo(dtype).max
        d_energy[idx] = maxValue + d_energy[idx] - max_dtype
    else:
        idx = d_energy <= 0
        d_energy[idx] = d_energy[idx] + maxValue

    d_energy = d_energy.astype("float32")

    total_energy = d_energy.sum()

    magFactor = raw_data.v_md.mag.value / Magnitude.ONE.value
    energy_J = total_energy * magFactor
    power_W = energy_J / runtime
    return energy_J, power_W


def processPowerData(
    raw_data: RawData,
    start: Optional[np.number] = None,
    end: Optional[np.number] = None,
) -> Tuple[Any, Any]:
    """Calculate energy and power from power time series.

    Using the start and end parameters the results can be limited to certain areas of the application run.

    Parameters
    ----------
    raw_data : RawData
        Raw Data from sensor
    start : Optional[np.number], optional
        Start time of region, by default None
    end : Optional[np.number], optional
        End time of region, by default None

    Returns
    -------
    _type_
       Tuple with total energy in joules and avg power in watts.
    """
    t_s = raw_data.timesteps.astype("float32")
    t_s *= raw_data.t_md.mag.value / Magnitude.ONE.value

    magFactor = raw_data.v_md.mag.value / Magnitude.ONE.value
    power_W = raw_data.values.astype("float32") * magFactor

    if start and end:
        t_s, power_W = getInterpolatedValues(t_s, power_W, start, end)

    avg_power_W = np.mean(power_W)
    energy_J = np.trapz(power_W, t_s)
    return energy_J, avg_power_W


def processSensorData(sensorData: DataNode) -> DataNode:
    """Calculate metrics based on raw values.

    Parameters
    ----------
    sensorData : DataNode
        DataNode with raw sensor data.

    Returns
    -------
    DataNode
        DataNode with computed metrics.
    """
    if sensorData.type == NodeType.SENSOR and sensorData.raw_data:
        rawData = sensorData.raw_data

        runtime = rawData.timesteps[-1]
        sensorData.metrics[MetricType.RUNTIME] = Metric(
            MetricType.RUNTIME, runtime, rawData.t_md, AggregateType.MAX
        )

        if rawData.v_md.unit == Unit.JOULE:
            energy_J, power_W = processEnergyData(rawData)

            energyMetric = Metric(
                MetricType.ENERGY,
                energy_J,
                MetricMetaData(
                    Unit.JOULE,
                    Magnitude.ONE,
                    np.dtype("float32"),
                    np.float32(0),
                    np.finfo("float32").max,
                    np.float32(-1),
                ),
                AggregateType.SUM,
            )
            powerMetric = Metric(
                MetricType.POWER,
                power_W,
                MetricMetaData(
                    Unit.WATT,
                    Magnitude.ONE,
                    np.dtype("float32"),
                    np.float32(0),
                    np.finfo("float32").max,
                    np.float32(-1),
                ),
                AggregateType.SUM,
            )

            sensorData.metrics[MetricType.ENERGY] = energyMetric
            sensorData.metrics[MetricType.POWER] = powerMetric

            if sensorData.deviceType == DeviceType.CPU:
                sensorData.metrics[MetricType.CPU_ENERGY] = energyMetric.copy()
                sensorData.metrics[MetricType.CPU_ENERGY].type = MetricType.CPU_ENERGY
                sensorData.metrics[MetricType.CPU_POWER] = powerMetric.copy()
                sensorData.metrics[MetricType.CPU_POWER].type = MetricType.CPU_POWER

            elif sensorData.deviceType == DeviceType.GPU:
                sensorData.metrics[MetricType.GPU_ENERGY] = energyMetric.copy()
                sensorData.metrics[MetricType.GPU_ENERGY].type = MetricType.GPU_ENERGY
                sensorData.metrics[MetricType.GPU_POWER] = powerMetric.copy()
                sensorData.metrics[MetricType.GPU_POWER].type = MetricType.GPU_POWER

            elif sensorData.deviceType == DeviceType.RAM:
                sensorData.metrics[MetricType.DRAM_ENERGY] = energyMetric.copy()
                sensorData.metrics[MetricType.DRAM_ENERGY].type = MetricType.DRAM_ENERGY
                sensorData.metrics[MetricType.DRAM_POWER] = powerMetric.copy()
                sensorData.metrics[MetricType.DRAM_POWER].type = MetricType.DRAM_POWER

            elif sensorData.deviceType == DeviceType.OTHER:
                sensorData.metrics[MetricType.OTHER_ENERGY] = energyMetric.copy()
                sensorData.metrics[
                    MetricType.OTHER_ENERGY
                ].type = MetricType.OTHER_ENERGY
                sensorData.metrics[MetricType.OTHER_POWER] = powerMetric.copy()
                sensorData.metrics[MetricType.OTHER_POWER].type = MetricType.OTHER_POWER

        elif rawData.v_md.unit == Unit.WATT:
            energy_J, power_W = processPowerData(rawData)
            energyMetric = Metric(
                MetricType.ENERGY,
                energy_J,
                MetricMetaData(
                    Unit.JOULE,
                    Magnitude.ONE,
                    np.dtype("float32"),
                    np.float32(0),
                    np.finfo("float32").max,
                    np.float32(-1),
                ),
                AggregateType.SUM,
            )
            powerMetric = Metric(
                MetricType.POWER,
                power_W,
                MetricMetaData(
                    Unit.WATT,
                    Magnitude.ONE,
                    np.dtype("float32"),
                    np.float32(0),
                    np.finfo("float32").max,
                    np.float32(-1),
                ),
                AggregateType.SUM,
            )

            sensorData.metrics[MetricType.ENERGY] = energyMetric
            sensorData.metrics[MetricType.POWER] = powerMetric

            if sensorData.deviceType == DeviceType.CPU:
                sensorData.metrics[MetricType.CPU_ENERGY] = energyMetric.copy()
                sensorData.metrics[MetricType.CPU_ENERGY].type = MetricType.CPU_ENERGY
                sensorData.metrics[MetricType.CPU_POWER] = powerMetric.copy()
                sensorData.metrics[MetricType.CPU_POWER].type = MetricType.CPU_POWER

            elif sensorData.deviceType == DeviceType.GPU:
                sensorData.metrics[MetricType.GPU_ENERGY] = energyMetric.copy()
                sensorData.metrics[MetricType.GPU_ENERGY].type = MetricType.GPU_ENERGY
                sensorData.metrics[MetricType.GPU_POWER] = powerMetric.copy()
                sensorData.metrics[MetricType.GPU_POWER].type = MetricType.GPU_POWER

            elif sensorData.deviceType == DeviceType.RAM:
                sensorData.metrics[MetricType.DRAM_ENERGY] = energyMetric.copy()
                sensorData.metrics[MetricType.DRAM_ENERGY].type = MetricType.DRAM_ENERGY
                sensorData.metrics[MetricType.DRAM_POWER] = powerMetric.copy()
                sensorData.metrics[MetricType.DRAM_POWER].type = MetricType.DRAM_POWER

            elif sensorData.deviceType == DeviceType.OTHER:
                sensorData.metrics[MetricType.OTHER_ENERGY] = energyMetric.copy()
                sensorData.metrics[
                    MetricType.OTHER_ENERGY
                ].type = MetricType.OTHER_ENERGY
                sensorData.metrics[MetricType.OTHER_POWER] = powerMetric.copy()
                sensorData.metrics[MetricType.OTHER_POWER].type = MetricType.OTHER_POWER

        elif rawData.v_md.unit == Unit.PERCENT:
            if sensorData.deviceType == DeviceType.CPU:
                metricType = MetricType.CPU_UTIL
            elif sensorData.deviceType == DeviceType.GPU:
                metricType = MetricType.GPU_UTIL
            else:
                metricType = MetricType.MEM_UTIL

            sensorData.metrics[metricType] = Metric(
                metricType,
                np.mean(rawData.values),
                rawData.v_md,
                AggregateType.MEAN,
            )
        elif rawData.v_md.unit == Unit.BYTE:
            bytes_v = rawData.values

            if sensorData.deviceType == DeviceType.NET:
                if "READ" in sensorData.id:
                    metricType = MetricType.NET_READ
                else:
                    metricType = MetricType.NET_WRITE

                d_bytes = bytes_v[1:] - bytes_v[:-1]
                result = d_bytes.sum()
                aggType = AggregateType.SUM
            elif sensorData.deviceType == DeviceType.DISK:
                if "READ" in sensorData.id:
                    metricType = MetricType.DISK_READ
                else:
                    metricType = MetricType.DISK_WRITE

                d_bytes = bytes_v[1:] - bytes_v[:-1]
                result = d_bytes.sum()
                aggType = AggregateType.SUM
            elif sensorData.deviceType == DeviceType.GPU:
                metricType = MetricType.GPU_MEM
                result = bytes_v.mean()
                aggType = AggregateType.SUM
            else:
                metricType = MetricType.OTHER_MEM
                result = bytes_v.mean()
                aggType = AggregateType.SUM

            sensorData.metrics[metricType] = Metric(
                metricType, result.astype(rawData.v_md.dtype), rawData.v_md, aggType
            )

        sensorData.processed = True
    return sensorData


def processDataNode(
    dataNode: DataNode, perunConfig: ConfigParser, force_process=False
) -> DataNode:
    """Recursively calculate metrics on the dataNode tree.

    Parameters
    ----------
    dataNode : DataNode
        Root data node tree.
    perunConfig: ConfigParser
        Perun configuration
    force_process : bool, optional
        Force recomputation of child node metrics, by default False

    Returns
    -------
    DataNode
        Data node with computed metrics.
    """
    # Regions
    if dataNode.regions:
        start = datetime.now()
        unprocessedRegions = []
        for region in dataNode.regions.values():
            if not region.processed:
                addRunAndRuntimeInfoToRegion(region)
                region.processed = True
                unprocessedRegions.append(region)

        processRegionsWithSensorData(unprocessedRegions, dataNode)
        duration = datetime.now() - start
        log.info(f"Region processing duration: {duration}")

    aggregatedMetrics: Dict[MetricType, List[Metric]] = {}
    for _, subNode in dataNode.nodes.items():
        # Make sure sub nodes have their metrics ready
        if not subNode.processed or force_process:
            if subNode.type == NodeType.SENSOR:
                subNode = processSensorData(subNode)
            else:
                subNode = processDataNode(
                    subNode, perunConfig=perunConfig, force_process=force_process
                )

        if dataNode.type == NodeType.APP:
            for subSubNode in subNode.nodes.values():
                for metricType, metric in subSubNode.metrics.items():
                    if isinstance(metric, Metric):
                        if metricType in aggregatedMetrics:
                            aggregatedMetrics[metricType].append(metric)
                        else:
                            aggregatedMetrics[metricType] = [metric]

        else:
            for metricType, metric in subNode.metrics.items():
                if isinstance(metric, Metric):
                    if metricType in aggregatedMetrics:
                        aggregatedMetrics[metricType].append(metric)
                    else:
                        aggregatedMetrics[metricType] = [metric]

    for metricType, metrics in aggregatedMetrics.items():
        aggType = metrics[0].agg
        metric_md = metrics[0].metric_md
        if dataNode.type == NodeType.MULTI_RUN or dataNode.type == NodeType.APP:
            dataNode.metrics[metricType] = Stats.fromMetrics(metrics)
        else:
            if aggType == AggregateType.MEAN:
                aggregatedValue = np.array([metric.value for metric in metrics]).mean()
            elif aggType == AggregateType.MAX:
                aggregatedValue = np.array([metric.value for metric in metrics]).max()
            elif aggType == AggregateType.MIN:
                aggregatedValue = np.array([metric.value for metric in metrics]).min()
            else:
                aggregatedValue = np.array([metric.value for metric in metrics]).sum()

            dataNode.metrics[metricType] = Metric(
                metricType, aggregatedValue, metric_md, aggType
            )

    # Apply power overhead to each computational node if there is power data available.
    if dataNode.type == NodeType.NODE and MetricType.POWER in dataNode.metrics:
        power_overhead = perunConfig.getfloat("post-processing", "power_overhead")
        dataNode.metrics[MetricType.POWER].value += power_overhead  # type: ignore
        runtime = dataNode.metrics[MetricType.RUNTIME].value
        dataNode.metrics[MetricType.ENERGY].value += runtime * power_overhead  # type: ignore

    # If there is energy data, apply PUE, and convert to currency and CO2 emmisions.
    if dataNode.type == NodeType.RUN and MetricType.ENERGY in dataNode.metrics:
        pue = perunConfig.getfloat("post-processing", "pue")
        emissions_factor = perunConfig.getfloat("post-processing", "emissions_factor")
        price_factor = perunConfig.getfloat("post-processing", "price_factor")
        total_energy = dataNode.metrics[MetricType.ENERGY].value * pue
        dataNode.metrics[MetricType.ENERGY].value = total_energy  # type: ignore
        e_kWh = total_energy / (3600 * 1e3)

        costMetric = Metric(
            MetricType.MONEY,
            e_kWh * price_factor,
            MetricMetaData(
                Unit.SCALAR,
                Magnitude.ONE,
                np.dtype("float32"),
                np.float32(0),
                np.finfo("float32").max,
                np.float32(0),
            ),
            AggregateType.SUM,
        )

        co2Emissions = Metric(
            MetricType.CO2,
            e_kWh * emissions_factor,
            MetricMetaData(
                Unit.GRAM,
                Magnitude.ONE,
                np.dtype("float32"),
                np.float32(0),
                np.finfo("float32").max,
                np.float32(0),
            ),
            AggregateType.SUM,
        )
        dataNode.metrics[MetricType.MONEY] = costMetric
        dataNode.metrics[MetricType.CO2] = co2Emissions

    dataNode.processed = True
    return dataNode


def processRegionsWithSensorData(regions: List[Region], dataNode: DataNode):
    """Complete region information using sensor data found on the data node (in place op).

    Parameters
    ----------
    regions : List[Region]
        List of regions that use the same data node.
    dataNode : DataNode
        Data node with sensor data.
    """
    world_size = regions[0].world_size
    power = [
        [
            [0.0 for _ in range(region.raw_data[rank].shape[0] // 2)]
            for rank in range(world_size)
        ]
        for region in regions
    ]
    cpu_util = copy.deepcopy(power)

    gpu_util = copy.deepcopy(power)
    gpu_count = copy.deepcopy(power)

    has_gpu = False

    for hostNode in dataNode.nodes.values():
        # Get relevant ranks
        ranks = hostNode.metadata["mpi_ranks"]
        for deviceNode in hostNode.nodes.values():
            if (
                deviceNode.deviceType == DeviceType.CPU
                or deviceNode.deviceType == DeviceType.GPU
                or deviceNode.deviceType == DeviceType.RAM
            ):
                for sensorNode in deviceNode.nodes.values():
                    if sensorNode.raw_data:
                        raw_data = sensorNode.raw_data
                        measuring_unit = raw_data.v_md.unit
                        for region_idx, region in enumerate(regions):
                            for rank in ranks:
                                if rank in region.raw_data:
                                    events = region.raw_data[rank]
                                    for i in range(events.shape[0] // 2):
                                        if measuring_unit == Unit.JOULE:
                                            _, power_W = processEnergyData(
                                                raw_data,
                                                events[i * 2],
                                                events[i * 2 + 1],
                                            )
                                            power[region_idx][rank][i] += power_W
                                        elif measuring_unit == Unit.WATT:
                                            _, power_W = processPowerData(
                                                raw_data,
                                                events[i * 2],
                                                events[i * 2 + 1],
                                            )
                                            power[region_idx][rank][i] += power_W
                                        elif (
                                            measuring_unit == Unit.PERCENT
                                            and deviceNode.deviceType == DeviceType.CPU
                                        ):
                                            _, values = getInterpolatedValues(
                                                raw_data.timesteps.astype("float32"),
                                                raw_data.values,
                                                events[i * 2],
                                                events[i * 2 + 1],
                                            )
                                            cpu_util[region_idx][rank][i] += np.mean(
                                                values
                                            )
                                        elif (
                                            measuring_unit == Unit.BYTE
                                            and deviceNode.deviceType == DeviceType.GPU
                                        ):
                                            has_gpu = True
                                            _, values = getInterpolatedValues(
                                                raw_data.timesteps.astype("float32"),
                                                raw_data.values,
                                                events[i * 2],
                                                events[i * 2 + 1],
                                            )
                                            gpu_util[region_idx][rank][i] += (
                                                np.mean(values)
                                                * 100
                                                / raw_data.v_md.max
                                            ).astype("float32")
                                            gpu_count[region_idx][rank][i] += 1

    for region_idx, region in enumerate(regions):
        r_power = np.array(list(chain(*power[region_idx])))
        r_cpu_util = np.array(list(chain(*cpu_util[region_idx])))

        r_gpu_util = np.array(list(chain(*gpu_util[region_idx])))
        r_gpu_count = np.array(list(chain(*gpu_count[region_idx])))

        if has_gpu:
            r_gpu_util /= r_gpu_count

        region.cpu_util = Stats(
            MetricType.CPU_UTIL,
            MetricMetaData(
                Unit.PERCENT,
                Magnitude.ONE,
                np.dtype("float32"),
                np.float32(0),
                np.float32(100),
                np.float32(-1),
            ),
            r_cpu_util.sum(),
            r_cpu_util.mean(),
            r_cpu_util.std(),
            r_cpu_util.max(),
            r_cpu_util.min(),
        )
        region.gpu_util = Stats(
            MetricType.GPU_UTIL,
            MetricMetaData(
                Unit.PERCENT,
                Magnitude.ONE,
                np.dtype("float32"),
                np.float32(0),
                np.float32(100),
                np.float32(-1),
            ),
            r_gpu_util.sum(),
            r_gpu_util.mean(),
            r_gpu_util.std(),
            r_gpu_util.max(),
            r_gpu_util.min(),
        )
        region.power = Stats(
            MetricType.POWER,
            MetricMetaData(
                Unit.WATT,
                Magnitude.ONE,
                np.dtype("float32"),
                np.float32(0),
                np.finfo("float32").max,
                np.float32(-1),
            ),
            r_power.sum(),
            r_power.mean(),
            r_power.std(),
            r_power.max(),
            r_power.min(),
        )


def addRunAndRuntimeInfoToRegion(region: Region):
    """Process run and runtime stats in region objects (in place operation).

    Parameters
    ----------
    region : Region
        Region object
    """
    runs_per_rank = []
    runtime = []

    for rank in range(region.world_size):
        if rank in region.raw_data:
            events = region.raw_data[rank]
            runs_per_rank.append(events.shape[0] / 2)
            for i in range(1, events.shape[0], 2):
                runtime.append(events[i] - events[i - 1])
        else:
            runs_per_rank.append(0)

    runs_array = np.array(runs_per_rank)
    runtime_array = np.array(runtime)

    region.runs_per_rank = Stats(
        MetricType.N_RUNS,
        MetricMetaData(
            Unit.SCALAR,
            Magnitude.ONE,
            np.dtype("float32"),
            np.float32(0),
            np.finfo("float32").max,
            np.float32(-1),
        ),
        runs_array.sum(),
        runs_array.mean(),
        runs_array.std(),
        runs_array.max(),
        runs_array.min(),
    )

    region.runtime = Stats(
        MetricType.RUNTIME,
        MetricMetaData(
            Unit.SECOND,
            Magnitude.ONE,
            np.dtype("float32"),
            np.float32(0),
            np.finfo("float32").max,
            np.float32(-1),
        ),
        runtime_array.sum(),
        runtime_array.mean(),
        runtime_array.std(),
        runtime_array.max(),
        runtime_array.min(),
    )


def getInterpolatedValues(
    t: np.ndarray, x: np.ndarray, start: np.number, end: np.number
) -> Tuple[np.ndarray, np.ndarray]:
    """Filter timeseries with a start and end limit, and interpolate the values at the edges.

    Parameters
    ----------
    t : np.ndarray
        Original time steps
    x : np.ndarray
        Original values
    start : np.number
        Start of the region of interest
    end : np.number
        End of the roi

    Returns
    -------
    np.ndarray
        ROI values
    """
    new_t = np.concatenate([[start], t[np.all([t >= start, t <= end], axis=0)], [end]])
    new_x = np.interp(new_t, t, x)
    return new_t, new_x
