"""Processing Module."""
from typing import Dict, List

import numpy as np

from perun.data_model.data import (
    AggregateType,
    DataNode,
    Metric,
    MetricType,
    NodeType,
    Stats,
)
from perun.data_model.measurement_type import Magnitude, MetricMetaData, Unit
from perun.data_model.sensor import DeviceType


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
            t_s = rawData.timesteps.astype("float32")
            t_s *= rawData.t_md.mag.value / Magnitude.ONE.value

            e_J = rawData.values
            maxValue = rawData.v_md.max
            dtype = rawData.v_md.dtype.name
            d_energy = e_J[1:] - e_J[:-1]
            if "uint" in dtype:
                idx = d_energy >= maxValue
                max_dtype = np.iinfo(dtype).max
                d_energy[idx] = maxValue + d_energy[idx] - max_dtype
            else:
                idx = d_energy <= 0
                d_energy[idx] = d_energy[idx] + maxValue
            total_energy = d_energy.sum()

            magFactor = rawData.v_md.mag.value / Magnitude.ONE.value
            energy_J = np.float32(total_energy) * magFactor

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
                energy_J / runtime,
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
            t_s = rawData.timesteps.astype("float32")
            t_s *= rawData.t_md.mag.value / Magnitude.ONE.value

            magFactor = rawData.v_md.mag.value / Magnitude.ONE.value
            power_W = rawData.values.astype("float32") * magFactor
            energy_J = np.trapz(power_W, t_s)
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
                np.mean(power_W),
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
            if sensorData.deviceType == DeviceType.NET:
                if "READ" in sensorData.id:
                    metricType = MetricType.NET_READ
                else:
                    metricType = MetricType.NET_WRITE
            else:
                if "READ" in sensorData.id:
                    metricType = MetricType.DISK_READ
                else:
                    metricType = MetricType.DISK_WRITE

            bytes_v = rawData.values
            maxValue = rawData.v_md.max
            dtype = rawData.v_md.dtype.name
            d_bytes = bytes_v[1:] - bytes_v[:-1]
            result = d_bytes.sum()

            sensorData.metrics[metricType] = Metric(
                metricType,
                result.astype(rawData.v_md.dtype),
                rawData.v_md,
                AggregateType.SUM,
            )

        sensorData.processed = True
    return sensorData


def processDataNode(dataNode: DataNode, force_process=False) -> DataNode:
    """Recursively calculate metrics on the dataNode tree.

    Parameters
    ----------
    dataNode : DataNode
        Root data node tree.
    force_process : bool, optional
        Force recomputation of child node metrics, by default False

    Returns
    -------
    DataNode
        Data node with computed metrics.
    """
    aggregatedMetrics: Dict[MetricType, List[Metric]] = {}
    for _, subNode in dataNode.nodes.items():
        # Make sure sub nodes have their metrics ready
        if not subNode.processed or force_process:
            if subNode.type == NodeType.SENSOR:
                subNode = processSensorData(subNode)
            else:
                subNode = processDataNode(subNode, force_process=force_process)

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

    dataNode.processed = True
    return dataNode
