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
    """Calculate metrics based on the data found on sensor nodes.

    Args:
        sensorData (DataNode): DataNode with raw data (SENSOR)
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

            sensorData.metrics[MetricType.ENERGY] = Metric(
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
            sensorData.metrics[MetricType.POWER] = Metric(
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
        elif rawData.v_md.unit == Unit.WATT:
            t_s = rawData.timesteps.astype("float32")
            t_s *= rawData.t_md.mag.value / Magnitude.ONE.value

            magFactor = rawData.v_md.mag.value / Magnitude.ONE.value
            power_W = rawData.values.astype("float32") * magFactor
            energy_J = np.trapz(power_W, t_s)
            sensorData.metrics[MetricType.ENERGY] = Metric(
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
            sensorData.metrics[MetricType.POWER] = Metric(
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

            result = rawData.values[-1] - rawData.values[0]
            sensorData.metrics[metricType] = Metric(
                metricType,
                result.astype(rawData.v_md.dtype),
                rawData.v_md,
                AggregateType.SUM,
            )

        sensorData.processed = True
    return sensorData


def processDataNode(dataNode: DataNode, force_process=False) -> DataNode:
    """Recursively calculate metrics of the current nodes, and of child nodes if necessary.

    Args:
        dataNode (DataNode): Root of the DataNode structure
        force_process (bool, optional): If true, ignored processed flag in child DataNodes. Defaults to False.
    """
    aggregatedMetrics: Dict[MetricType, List[Metric]] = {}
    for _, subNode in dataNode.nodes.items():
        # Make sure sub nodes have their metrics ready
        if not subNode.processed or force_process:
            if subNode.type == NodeType.SENSOR:
                subNode = processSensorData(subNode)
            else:
                subNode = processDataNode(subNode, force_process=force_process)

        for metricType, metric in subNode.metrics.items():
            if isinstance(metric, Metric):
                if metricType in aggregatedMetrics:
                    aggregatedMetrics[metricType].append(metric)
                else:
                    aggregatedMetrics[metricType] = [metric]

    for metricType, metrics in aggregatedMetrics.items():
        aggType = metrics[0].agg
        metric_md = metrics[0].metric_md
        if dataNode.type == NodeType.MULTI_RUN:
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
