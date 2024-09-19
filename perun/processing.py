"""Processing Module."""

import copy
import logging
from configparser import ConfigParser
from datetime import datetime
from itertools import chain
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from perun.data_model.data import (
    DataNode,
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
    """Calculate total energy and average power from an energy or power time series.

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

    if raw_data.v_md.unit == Unit.JOULE:
        # If getting energy, transform to power
        e_J = raw_data.values
        maxValue = raw_data.v_md.max
        dtype = raw_data.v_md.dtype.name

        d_energy = np.diff(e_J)

        if "uint" in dtype:
            idx = d_energy >= maxValue
            max_dtype = np.iinfo(dtype).max
            d_energy[idx] = maxValue + d_energy[idx] - max_dtype
        else:
            idx = d_energy <= 0
            d_energy[idx] = d_energy[idx] + maxValue

        d_energy = d_energy.astype("float32")

        # Transform the energy series to a power series
        power_W = d_energy / np.diff(t_s)
        power_W = np.insert(power_W, 0, power_W[0])
        power_W *= magFactor

        raw_data.alt_values = e_J
        raw_data.alt_v_md = raw_data.v_md

        raw_data.values = power_W
        raw_data.v_md = MetricMetaData(
            Unit.WATT,
            Magnitude.ONE,
            np.dtype("float32"),
            np.float32(0),
            np.finfo("float32").max,
            np.float32(-1),
        )

    elif raw_data.v_md.unit == Unit.WATT:
        power_W = raw_data.values.astype("float32") * magFactor

    if start and end:
        t_s, power_W = getInterpolatedValues(t_s, power_W, start, end)

    avg_power_W = np.mean(power_W)
    energy_J = np.trapz(power_W, x=t_s)
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
        sensorData.stats[MetricType.RUNTIME] = Stats(
            MetricType.RUNTIME,
            rawData.t_md,
            runtime,
            runtime,
            0,
            runtime,
            runtime,
        )

        if rawData.v_md.unit == Unit.JOULE or rawData.v_md.unit == Unit.WATT:
            energy_J, avg_power_W = processEnergyData(rawData)

            energyMetric = Stats(
                MetricType.ENERGY,
                MetricMetaData(
                    Unit.JOULE,
                    Magnitude.ONE,
                    np.dtype("float32"),
                    np.float32(0),
                    np.finfo("float32").max,
                    np.float32(-1),
                ),
                energy_J,
                energy_J,
                0,
                energy_J,
                energy_J,
            )
            powerMetric = Stats(
                MetricType.POWER,
                MetricMetaData(
                    Unit.WATT,
                    Magnitude.ONE,
                    np.dtype("float32"),
                    np.float32(0),
                    np.finfo("float32").max,
                    np.float32(-1),
                ),
                avg_power_W,
                avg_power_W,
                np.std(rawData.values),
                np.max(rawData.values),
                np.min(rawData.values),
            )

            sensorData.stats[MetricType.ENERGY] = energyMetric
            sensorData.stats[MetricType.POWER] = powerMetric

            if sensorData.deviceType == DeviceType.CPU:
                sensorData.stats[MetricType.CPU_ENERGY] = energyMetric.copy()
                sensorData.stats[MetricType.CPU_ENERGY].type = MetricType.CPU_ENERGY
                sensorData.stats[MetricType.CPU_POWER] = powerMetric.copy()
                sensorData.stats[MetricType.CPU_POWER].type = MetricType.CPU_POWER

            elif sensorData.deviceType == DeviceType.GPU:
                sensorData.stats[MetricType.GPU_ENERGY] = energyMetric.copy()
                sensorData.stats[MetricType.GPU_ENERGY].type = MetricType.GPU_ENERGY
                sensorData.stats[MetricType.GPU_POWER] = powerMetric.copy()
                sensorData.stats[MetricType.GPU_POWER].type = MetricType.GPU_POWER

            elif sensorData.deviceType == DeviceType.RAM:
                sensorData.stats[MetricType.DRAM_ENERGY] = energyMetric.copy()
                sensorData.stats[MetricType.DRAM_ENERGY].type = MetricType.DRAM_ENERGY
                sensorData.stats[MetricType.DRAM_POWER] = powerMetric.copy()
                sensorData.stats[MetricType.DRAM_POWER].type = MetricType.DRAM_POWER

            elif sensorData.deviceType == DeviceType.OTHER:
                sensorData.stats[MetricType.OTHER_ENERGY] = energyMetric.copy()
                sensorData.stats[MetricType.OTHER_ENERGY].type = MetricType.OTHER_ENERGY
                sensorData.stats[MetricType.OTHER_POWER] = powerMetric.copy()
                sensorData.stats[MetricType.OTHER_POWER].type = MetricType.OTHER_POWER

        elif rawData.v_md.unit == Unit.PERCENT:
            if sensorData.deviceType == DeviceType.CPU:
                metricType = MetricType.CPU_UTIL
            elif sensorData.deviceType == DeviceType.GPU:
                metricType = MetricType.GPU_UTIL
            else:
                metricType = MetricType.OTHER_UTIL

            sensorData.stats[metricType] = Stats(
                metricType,
                rawData.v_md,
                np.mean(rawData.values),
                np.mean(rawData.values),
                np.std(rawData.values),
                np.max(rawData.values),
                np.min(rawData.values),
            )
        elif rawData.v_md.unit == Unit.BYTE:
            bytes_v = rawData.values

            if sensorData.deviceType == DeviceType.NET:
                if "READ" in sensorData.id:
                    metricType = MetricType.NET_READ
                else:
                    metricType = MetricType.NET_WRITE

                result = bytes_v[1:] - bytes_v[:-1]
            elif sensorData.deviceType == DeviceType.DISK:
                if "READ" in sensorData.id:
                    metricType = MetricType.DISK_READ
                else:
                    metricType = MetricType.DISK_WRITE

                result = bytes_v[1:] - bytes_v[:-1]
            elif sensorData.deviceType == DeviceType.GPU:
                metricType = MetricType.GPU_MEM
                result = bytes_v
            elif sensorData.deviceType == DeviceType.RAM:
                metricType = MetricType.DRAM_MEM
                result = bytes_v
            else:
                metricType = MetricType.OTHER_MEM
                result = bytes_v

            result = result.astype(rawData.v_md.dtype)
            sensorData.stats[metricType] = Stats(
                metricType,
                rawData.v_md,
                np.sum(result),
                np.mean(result),
                np.std(result),
                np.max(result),
                np.min(result),
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

    aggregatedStats: Dict[MetricType, List[Stats]] = {}
    for _, subNode in dataNode.nodes.items():
        # Make sure sub nodes have their metrics ready
        if not subNode.processed or force_process:
            if subNode.type == NodeType.SENSOR:
                subNode = processSensorData(subNode)
            else:
                subNode = processDataNode(
                    subNode, perunConfig=perunConfig, force_process=force_process
                )

        # Why did we need a special case for the APP node?
        if dataNode.type == NodeType.APP:
            for subSubNode in subNode.nodes.values():
                for metricType, metric in subSubNode.stats.items():
                    if metricType in aggregatedStats:
                        aggregatedStats[metricType].append(metric)
                    else:
                        aggregatedStats[metricType] = [metric]

        else:
            for metricType, metric in subNode.stats.items():
                if metricType in aggregatedStats:
                    aggregatedStats[metricType].append(metric)
                else:
                    aggregatedStats[metricType] = [metric]

    for metricType, stats in aggregatedStats.items():
        dataNode.stats[metricType] = Stats.fromStats(stats)

    # Apply power overhead to each computational node if there is power data available.
    if dataNode.type == NodeType.NODE and MetricType.POWER in dataNode.stats:
        power_overhead = perunConfig.getfloat("post-processing", "power_overhead")
        dataNode.stats[MetricType.POWER].value += power_overhead  # type: ignore
        runtime = dataNode.stats[MetricType.RUNTIME].max
        dataNode.stats[MetricType.ENERGY].value += runtime * power_overhead  # type: ignore

    # If there is energy data, apply PUE, and convert to currency and CO2 emmisions.
    if dataNode.type == NodeType.RUN and MetricType.ENERGY in dataNode.metrics:
        pue = perunConfig.getfloat("post-processing", "pue")
        emissions_factor = perunConfig.getfloat("post-processing", "emissions_factor")
        price_factor = perunConfig.getfloat("post-processing", "price_factor")
        total_energy = dataNode.stats[MetricType.ENERGY].value * pue  # type: ignore
        dataNode.stats[MetricType.ENERGY].value = total_energy  # type: ignore
        e_kWh = total_energy / (3600 * 1e3)

        cost_value = e_kWh * price_factor
        costMetric = Stats(
            MetricType.MONEY,
            MetricMetaData(
                Unit.SCALAR,
                Magnitude.ONE,
                np.dtype("float32"),
                np.float32(0),
                np.finfo("float32").max,
                np.float32(0),
            ),
            cost_value,
            cost_value,
            0,
            cost_value,
            cost_value,
        )

        co2_value = e_kWh * emissions_factor
        co2Emissions = Stats(
            MetricType.CO2,
            MetricMetaData(
                Unit.GRAM,
                Magnitude.ONE,
                np.dtype("float32"),
                np.float32(0),
                np.finfo("float32").max,
                np.float32(0),
            ),
            co2_value,
            co2_value,
            0,
            co2_value,
            co2_value,
        )
        dataNode.stats[MetricType.MONEY] = costMetric
        dataNode.stats[MetricType.CO2] = co2Emissions

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
    log.debug(f"Processing regions with sensor data: {len(regions)}")
    power = [
        {
            rank: [0.0 for _ in range(region.raw_data[rank].shape[0] // 2)]
            for rank in region.raw_data.keys()
        }
        for region in regions
    ]
    cpu_util = copy.deepcopy(power)
    dram_mem = copy.deepcopy(power)
    gpu_mem = copy.deepcopy(power)

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
                                        if (
                                            measuring_unit == Unit.JOULE
                                            or measuring_unit == Unit.WATT
                                        ):
                                            _, power_W = processEnergyData(
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
                                                values, dtype="float32"
                                            )
                                        elif (
                                            measuring_unit == Unit.BYTE
                                            and deviceNode.deviceType == DeviceType.RAM
                                        ):
                                            _, values = getInterpolatedValues(
                                                raw_data.timesteps.astype("float32"),
                                                raw_data.values,
                                                events[i * 2],
                                                events[i * 2 + 1],
                                            )
                                            dram_mem[region_idx][rank][i] += (
                                                np.mean(values)
                                            ).astype("float32")
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
                                            gpu_mem[region_idx][rank][i] += (
                                                np.mean(values)
                                            ).astype("float32")

    for region_idx, region in enumerate(regions):
        r_power = np.array(list(chain(*power[region_idx].values())))
        r_cpu_util = np.array(list(chain(*cpu_util[region_idx].values())))
        r_gpu_mem = np.array(list(chain(*gpu_mem[region_idx].values())))
        r_dram_mem = np.array(list(chain(*dram_mem[region_idx].values())))

        region.metrics[MetricType.CPU_UTIL] = Stats(
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
        region.metrics[MetricType.DRAM_MEM] = Stats(
            MetricType.DRAM_MEM,
            MetricMetaData(
                Unit.BYTE,
                Magnitude.ONE,
                np.dtype("uint64"),
                np.uint64(0),
                np.iinfo("uint64").max,  # type: ignore
                np.uint64(0),
            ),
            r_dram_mem.sum(),
            r_dram_mem.mean(),
            r_dram_mem.std(),
            r_dram_mem.max(),
            r_dram_mem.min(),
        )
        region.metrics[MetricType.POWER] = Stats(
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
        if has_gpu:
            region.metrics[MetricType.GPU_MEM] = Stats(
                MetricType.GPU_MEM,
                MetricMetaData(
                    Unit.BYTE,
                    Magnitude.ONE,
                    np.dtype("uint64"),
                    np.uint64(0),
                    np.iinfo("uint64").max,  # type: ignore
                    np.uint64(0),
                ),
                r_gpu_mem.sum(),
                r_gpu_mem.mean(),
                r_gpu_mem.std(),
                r_gpu_mem.max(),
                r_gpu_mem.min(),
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

    for rank in region.raw_data.keys():
        events = region.raw_data[rank]
        runs_per_rank.append(events.shape[0] / 2)
        for i in range(1, events.shape[0], 2):
            runtime.append(events[i] - events[i - 1])

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

    region.metrics[MetricType.RUNTIME] = Stats(
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
    new_x = np.interp(new_t, t, x)  # type: ignore
    return new_t, new_x
