"""Processing Module."""
import numpy as np

from perun.data_model.data import AggregateType, DataNode, Metric, MetricType, NodeType
from perun.data_model.measurement_type import Magnitude, MetricMetaData, Unit
from perun.data_model.sensor import DeviceType


def processSensorData(sensorData: DataNode):
    """Calculate metrics based on the data found on sensor nodes.

    Args:
        sensorData (DataNode): DataNode with raw data (SENSOR)
    """
    if sensorData.type == NodeType.SENSOR and sensorData.raw_data:
        rawData = sensorData.raw_data

        runtime = rawData.timesteps[-1] - rawData.timesteps[0]
        sensorData.addMetric(
            Metric(MetricType.RUNTIME, runtime, rawData.t_md, AggregateType.MAX)
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

            sensorData.addMetric(
                Metric(
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
            )
            sensorData.addMetric(
                Metric(
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
            )

        elif rawData.v_md.unit == Unit.WATT:
            t_s = rawData.timesteps.astype("float32")
            t_s *= rawData.t_md.mag.value / Magnitude.ONE.value

            magFactor = rawData.v_md.mag.value / Magnitude.ONE.value
            power_W = rawData.values.astype("float32") * magFactor
            energy_J = np.trapz(power_W, t_s)
            sensorData.addMetric(
                Metric(
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
            )
            sensorData.addMetric(
                Metric(
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
            )
        elif rawData.v_md.unit == Unit.PERCENT:
            if sensorData.deviceType == DeviceType.CPU:
                metricType = MetricType.CPU_UTIL
            elif sensorData.deviceType == DeviceType.GPU:
                metricType = MetricType.GPU_UTIL
            else:
                metricType = MetricType.MEM_UTIL

            sensorData.addMetric(
                Metric(
                    metricType,
                    np.mean(rawData.values),
                    rawData.v_md,
                    AggregateType.MEAN,
                )
            )
        elif rawData.v_md.unit == Unit.BYTE:
            if sensorData.deviceType == DeviceType.NETWORK:
                if "READ" in sensorData.id:
                    metricType = MetricType.NET_READ
                else:
                    metricType = MetricType.NET_WRITE
            else:
                if "READ" in sensorData.id:
                    metricType = MetricType.FS_READ
                else:
                    metricType = MetricType.FS_WRITE

            result = rawData.values[-1] - rawData.values[0]
            sensorData.addMetric(
                Metric(
                    metricType,
                    result.astype(rawData.v_md.dtype),
                    rawData.v_md,
                    AggregateType.SUM,
                )
            )

        sensorData.processed = True


# def processDeviceGroupData(deviceNode: DataNode, force_process: bool=True):
#     pass

# def processNodeData(deviceNode: DataNode, force_process: bool=True):
#     pass

# def processRunData(runNode: DataNode, force_process: bool=True):
#     pass
