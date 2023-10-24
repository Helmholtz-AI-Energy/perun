"""Perun subprocess module."""
import logging
import platform
import time
from configparser import ConfigParser
from multiprocessing import Queue
from typing import Dict, List, Set

import numpy as np

from perun.backend.backend import Backend
from perun.data_model.data import DataNode, NodeType, RawData
from perun.data_model.measurement_type import Magnitude, MetricMetaData, Unit
from perun.data_model.sensor import DeviceType, Sensor
from perun.processing import processDataNode, processSensorData

log = logging.getLogger("perun")


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
    lSensors: List[Sensor] = []
    log.debug(f"SP: backends -- {backends}")
    log.debug(f"SP: l_sensor_config -- {l_sensors_config}")
    for backend in backends.values():
        if backend.name in l_sensors_config:
            lSensors += backend.getSensors(l_sensors_config[backend.name])

    timesteps = []
    t_mT = MetricMetaData(
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

    log.debug(f"Rank {rank}: perunSP lSensors: {lSensors}")

    # Monitoring process ready
    sp_ready_event.set()

    # Waiting for main process to send the signal
    start_event.wait()
    timesteps.append(time.time_ns())
    for idx, device in enumerate(lSensors):
        rawValues[idx].append(device.read())

    while not stop_event.wait(sampling_rate):
        timesteps.append(time.time_ns())
        for idx, device in enumerate(lSensors):
            rawValues[idx].append(device.read())

    timesteps.append(time.time_ns())
    for idx, device in enumerate(lSensors):
        rawValues[idx].append(device.read())

    log.info(f"Rank {rank}: Subprocess: Stop event received.")

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
            raw_data=RawData(t_s, np.array(values), t_mT, sensor.dataType),
        )
        # Apply processing to sensor node
        dn = processSensorData(dn)
        sensorNodes[sensor.type].append(dn)

    log.info(f"Rank {rank}: Subprocess: Preprocessed Sensor Data")
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

    log.info(f"Rank {rank}: Subprocess: Preprocessed Device Data")

    hostNode = DataNode(
        id=platform.node(),
        type=NodeType.NODE,
        metadata={},
        nodes={node.id: node for node in deviceGroupNodes},
    )
    processDataNode(hostNode, perunConfig)

    # This should send a single processed node for the current computational node
    queue.put(hostNode, block=True)
    log.info(f"Rank {rank}: Subprocess: Sent data")
