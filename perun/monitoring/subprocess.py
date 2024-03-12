"""Perun subprocess module."""

import logging
import platform
import time
from configparser import ConfigParser
from multiprocessing import Queue
from typing import Callable, Dict, List, Set, Tuple

import numpy as np

from perun.backend.backend import Backend
from perun.data_model.data import DataNode, NodeType, RawData
from perun.data_model.measurement_type import Magnitude, MetricMetaData, Unit
from perun.data_model.sensor import DeviceType, Sensor
from perun.processing import processDataNode, processSensorData

log = logging.getLogger("perun")


def _prepSensors(
    backends: Dict[str, Backend], l_sensors_config: Dict[str, Set[str]]
) -> Tuple[List[int], MetricMetaData, List[List[np.number]], List[Sensor]]:
    lSensors: List[Sensor] = []
    for backend in backends.values():
        if backend.name in l_sensors_config:
            lSensors += backend.getSensors(l_sensors_config[backend.name])

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
    stopCondition: Callable[[], bool],
):
    timesteps.append(time.time_ns())
    for idx, device in enumerate(lSensors):
        rawValues[idx].append(device.read())

    while not stopCondition():
        timesteps.append(time.time_ns())
        for idx, device in enumerate(lSensors):
            rawValues[idx].append(device.read())

    timesteps.append(time.time_ns())
    for idx, device in enumerate(lSensors):
        rawValues[idx].append(device.read())
    return


def _createNode(
    timesteps: List[int],
    t_metadata: MetricMetaData,
    rawValues: List[List[np.number]],
    lSensors: List[Sensor],
    perunConfig: ConfigParser,
) -> DataNode:
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
    l_sensors_config: Dict[str, Set[str]],
    perunConfig: ConfigParser,
    sp_ready_event,
    start_event,
    stop_event,
    sampling_rate: float,
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
    l_sensors_config : Dict[str, Set[str]]
        Local MPI rank sensor configuration
    sp_ready_event : _type_
        Indicates monitoring supbrocess is ready, multiprocessing module
    start_event : _type_
        Indicates app start, multiprocessing module
    stop_event : _type_
        Indicates app stop, multiprocessing module
    sampling_rate : float
        Sampling rate in seconds
    """
    (
        timesteps,
        t_metadata,
        rawValues,
        lSensors,
    ) = _prepSensors(backends, l_sensors_config)
    log.debug(f"SP: backends -- {backends}")
    log.debug(f"SP: l_sensor_config -- {l_sensors_config}")
    log.debug(f"Rank {rank}: perunSP lSensors: {lSensors}")

    # Monitoring process ready
    sp_ready_event.set()

    # Waiting for main process to send the signal
    start_event.wait()
    _monitoringLoop(
        lSensors, timesteps, rawValues, lambda: stop_event.wait(sampling_rate)
    )

    log.info(f"Rank {rank}: Subprocess: Stop event received.")
    hostNode = _createNode(timesteps, t_metadata, rawValues, lSensors, perunConfig)

    processDataNode(hostNode, perunConfig)

    # This should send a single processed node for the current computational node
    queue.put(hostNode, block=True)
    log.info(f"Rank {rank}: Subprocess: Sent data")
    return hostNode
