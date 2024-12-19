"""Perun subprocess module."""

import logging
import platform
import time
from configparser import ConfigParser
from multiprocessing import Queue
from typing import Callable, Dict, List, Tuple

import numpy as np

from perun.backend.backend import Backend
from perun.data_model.data import DataNode, NodeType, RawData
from perun.data_model.measurement_type import Magnitude, MetricMetaData, Unit
from perun.data_model.sensor import DeviceType, Sensor
from perun.processing import processDataNode, processSensorData

log = logging.getLogger("perun")


def prepSensors(
    backends: Dict[str, Backend], l_assigned_sensors: Dict[str, Tuple]
) -> Tuple[List[int], MetricMetaData, List[List[np.number]], List[Sensor]]:
    """
    Prepare sensors for monitoring.

    Parameters
    ----------
    backends : Dict[str, Backend]
        A dictionary of backends.
    l_assigned_sensors : Dict[str, Tuple]
        A dictionary of sensor configurations.

    Returns
    -------
    Tuple[List[int], MetricMetaData, List[List[np.number]], List[Sensor]]
        A tuple containing the following:
        - timesteps (List[int]): A list of timesteps.
        - t_metadata (MetricMetaData): Metadata for the metrics.
        - rawValues (List[List[np.number]]): A list of raw sensor values.
        - lSensors (List[Sensor]): A list of sensors.
    """
    lSensors: List[Sensor] = []
    for backend in backends.values():
        sensor_ids = {
            sensor_id
            for sensor_id, sensor_md in l_assigned_sensors.items()
            if sensor_md[0] == backend.id
        }
        if len(sensor_ids) > 0:
            lSensors += backend.getSensors(sensor_ids)

    timesteps: List[int] = []
    t_metadata = MetricMetaData(
        Unit.SECOND,
        Magnitude.ONE,
        np.dtype("float32"),
        np.float32(0),
        np.finfo("float32").max,
        np.float32(-1),
    )
    rawValues: List[List[np.number]] = []
    for _ in lSensors:
        rawValues.append([])

    return timesteps, t_metadata, rawValues, lSensors


def _monitoringLoop(
    lSensors: List[Sensor],
    timesteps: List[int],
    rawValues: List[List[np.number]],
    stopCondition: Callable[[float], bool],
):
    timesteps.append(time.time_ns())
    for idx, device in enumerate(lSensors):
        rawValues[idx].append(device.read())

    delta = (time.time_ns() - timesteps[-1]) * 1e-9
    while not stopCondition(delta):
        timesteps.append(time.time_ns())
        for idx, device in enumerate(lSensors):
            rawValues[idx].append(device.read())
        delta = (time.time_ns() - timesteps[-1]) * 1e-9

    timesteps.append(time.time_ns())
    for idx, device in enumerate(lSensors):
        rawValues[idx].append(device.read())
    return


def createNode(
    timesteps: List[int],
    t_metadata: MetricMetaData,
    rawValues: List[List[np.number]],
    lSensors: List[Sensor],
    perunConfig: ConfigParser,
) -> DataNode:
    """
    Create a data node from the sensor data.

    Parameters
    ----------
    timesteps : List[int]
        A list of timesteps.
    t_metadata : MetricMetaData
        Metadata for the metrics.
    rawValues : List[List[np.number]]
        A list of raw sensor values.
    lSensors : List[Sensor]
        A list of sensors.
    perunConfig : ConfigParser
        The perun configuration.

    Returns
    -------
    DataNode
        A data node.
    """
    sensorNodes: Dict = {}

    t_s = np.array(timesteps)
    t_s -= t_s[0]
    t_s = t_s.astype("float32")
    t_s *= 1e-9

    for sensor, values in zip(lSensors, rawValues):
        if sensor.type not in sensorNodes:
            sensorNodes[sensor.type] = []

        dn = DataNode(
            id=sensor.id,
            type=NodeType.SENSOR,
            metadata=sensor.metadata,
            deviceType=sensor.type,
            raw_data=RawData(t_s, np.array(values), t_metadata, sensor.dataType),
        )
        # Apply processing to sensor node
        dn = processSensorData(dn)
        sensorNodes[sensor.type].append(dn)

    deviceGroupNodes = []
    for deviceType, sensorNodes in sensorNodes.items():
        if deviceType != DeviceType.NODE:
            dn = DataNode(
                id=deviceType.value,
                type=NodeType.DEVICE_GROUP,
                metadata={},
                nodes={sensor.id: sensor for sensor in sensorNodes},
                deviceType=deviceType,
            )

            dn = processDataNode(dn, perunConfig)
            deviceGroupNodes.append(dn)
        else:
            deviceGroupNodes.extend(sensorNodes)

    hostNode = DataNode(
        id=platform.node(),
        type=NodeType.NODE,
        metadata={},
        nodes={node.id: node for node in deviceGroupNodes},
    )
    return hostNode


def perunSubprocess(
    queue: Queue,
    rank: int,
    backends: Dict[str, Backend],
    l_assigned_sensors: Dict[str, Tuple],
    perunConfig: ConfigParser,
    sp_ready_event,
    start_event,
    stop_event,
    sampling_period: float,
):
    """Parallel function that samples energy values from hardware libraries.

    Parameters
    ----------
    queue : Queue
        Multiprocessing Queue object where the results are sent after finish
    rank : int
        Local MPI Rank
    backends : List[Backend]
        Available backend list
    l_assigned_sensors : Dict[str, Tuple]
        Local MPI rank sensor configuration
    sp_ready_event : _type_
        Indicates monitoring supbrocess is ready, multiprocessing module
    start_event : _type_
        Indicates app start, multiprocessing module
    stop_event : _type_
        Indicates app stop, multiprocessing module
    sampling_period : float
        Sampling period in seconds
    """
    log.debug(f"Rank {rank}: Subprocess: Entered perunSubprocess")
    (
        timesteps,
        t_metadata,
        rawValues,
        lSensors,
    ) = prepSensors(backends, l_assigned_sensors)
    log.debug(f"SP: backends -- {backends}")
    log.debug(f"SP: l_sensor_config -- {l_assigned_sensors}")
    log.debug(f"Rank {rank}: perunSP lSensors: {lSensors}")

    # Monitoring process ready
    sp_ready_event.set()

    # Waiting for main process to send the signal
    start_event.wait()
    _monitoringLoop(
        lSensors,
        timesteps,
        rawValues,
        lambda delta: stop_event.wait(sampling_period - delta),
    )

    log.info(f"Rank {rank}: Subprocess: Stop event received.")
    hostNode = createNode(timesteps, t_metadata, rawValues, lSensors, perunConfig)

    processDataNode(hostNode, perunConfig)

    # This should send a single processed node for the current computational node
    queue.put(hostNode, block=True)
    log.info(f"Rank {rank}: Subprocess: Sent data")
    return hostNode
