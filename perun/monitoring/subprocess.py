"""Perun subprocess module."""

import logging
import platform
import time
from configparser import ConfigParser
from multiprocessing import Queue
from multiprocessing.synchronize import Event as EventClass
from typing import Callable, Dict, List, Tuple

import numpy as np

from perun.backend import Backend, available_backends
from perun.data_model.data import DataNode, NodeType, RawData
from perun.data_model.measurement_type import Magnitude, MetricMetaData, Number, Unit
from perun.data_model.sensor import DeviceType, Sensor
from perun.processing import processDataNode, processSensorData

log = logging.getLogger(__name__)


def prepSensors(
    backends: Dict[str, Backend], l_assigned_sensors: Dict[str, Tuple]
) -> Tuple[MetricMetaData, List[Sensor]]:
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
    Tuple[List[int], MetricMetaData, List[List[Number]], List[Sensor]]
        A tuple containing the following:
        - timesteps (List[int]): A list of timesteps.
        - t_metadata (MetricMetaData): Metadata for the metrics.
        - rawValues (List[List[Number]]): A list of raw sensor values.
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

    t_metadata = MetricMetaData(
        Unit.SECOND,
        Magnitude.ONE,
        np.dtype("float32"),
        np.float32(0),
        np.finfo("float32").max,
        np.float32(-1),
    )

    return t_metadata, lSensors


def _monitoringLoop(
    lSensors: List[Sensor],
    timesteps: List[int],
    rawValues: List[List[Number]],
    stopCondition: Callable[[float], bool],
    callbacks: List[Callable[[dict[str, Number]], None]] = [],
) -> None:
    timesteps.append(time.time_ns())
    values: dict[str, Number] = {}
    hostname = platform.node()
    for idx, device in enumerate(lSensors):
        value = device.read()
        rawValues[idx].append(value)
        values[f"{hostname}_{device.id}"] = value

    for callback in callbacks:
        callback(values)

    delta = (time.time_ns() - timesteps[-1]) * 1e-9
    while not stopCondition(delta):
        timesteps.append(time.time_ns())
        for idx, device in enumerate(lSensors):
            value = device.read()
            rawValues[idx].append(value)
            values[f"{hostname}_{device.id}"] = value

        for callback in callbacks:
            callback(values)
        delta = (time.time_ns() - timesteps[-1]) * 1e-9

    timesteps.append(time.time_ns())
    for idx, device in enumerate(lSensors):
        value = device.read()
        rawValues[idx].append(value)
        values[f"{hostname}_{device.id}"] = value

    for callback in callbacks:
        callback(values)

    return


def createNode(
    timesteps: List[int],
    t_metadata: MetricMetaData,
    rawValues: List[List[Number]],
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
    rawValues : List[List[Number]]
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
    l_assigned_sensors: Dict[str, Tuple],
    perunConfig: ConfigParser,
    sp_ready_event: EventClass,
    start_event: EventClass,
    stop_event: EventClass,
    close_event: EventClass,
    sampling_period: float,
    live_callback_inits: dict[str, Callable[[], Callable[[str, Number], None]]],
) -> None:
    """Parallel function that samples energy values from hardware libraries.

    Parameters
    ----------
    queue : Queue
        Multiprocessing Queue object where the results are sent after finish
    rank : int
        Local MPI Rank
    l_assigned_sensors : Dict[str, Tuple]
        Local MPI rank sensor configuration
    perunConfig: ConfigParser
        Global perun configuration
    sp_ready_event : EventClass
        Indicates monitoring supbrocess is ready, multiprocessing module
    start_event : EventClass
        Indicates start of the monitored application
    stop_event : EventClass
        Indicates the stop of a monitored application
    close_event : EventClass
        Indicates that perun is closing, and the subprocess needs to close
    sampling_period : float
        Sampling period in seconds
    live_callback_inits : dict[str, Callable[[], Callable[[str, Number], None]]]
        Dictionary of live callback initializers, where the key is the name of the callback and the value is a function that returns a callable that accepts metric identifier and value.
    """
    log.info(f"Rank {rank}: Subprocess: Starting perunSubprocess")
    backends: Dict[str, Backend] = {}
    for name, backend_class in available_backends.items():
        try:
            backend_instance = backend_class()
            backends[backend_instance.id] = backend_instance
        except ImportError as ie:
            log.info(f"Missing dependencies for backend {name}")
            log.info(ie)
        except Exception as e:
            log.info(f"Unknown error loading dependecy {name}")
            log.info(e)
    log.info("Subprocess: Initialized backends.")
    (
        t_metadata,
        lSensors,
    ) = prepSensors(backends, l_assigned_sensors)

    # Initializing live callbacks:
    callbacks = []
    for init_func in live_callback_inits.values():
        callbacks.append(init_func())
    log.info(f"Subprocess: Initialized {len(callbacks)} live callbacks.")

    # Reset
    timesteps: List[int] = []
    rawValues: List[List[Number]] = []
    for _ in lSensors:
        rawValues.append([])
    log.debug(f"SP: backends -- {backends}")
    log.debug(f"SP: l_sensor_config -- {l_assigned_sensors}")
    log.debug(f"Rank {rank}: perunSP lSensors: {lSensors}")

    # Monitoring process ready
    monitoring = True
    sp_ready_event.set()

    while monitoring:
        if start_event.is_set():
            start_event.clear()
            _monitoringLoop(
                lSensors,
                timesteps,
                rawValues,
                lambda delta: stop_event.wait(sampling_period - delta),
                callbacks,
            )
            stop_event.clear()

            log.info(f"Rank {rank}: Subprocess: Stop event received.")
            hostNode = createNode(
                timesteps, t_metadata, rawValues, lSensors, perunConfig
            )
            log.info(f"Rank {rank}: Subprocess: Created data node: {hostNode}")

            processDataNode(hostNode, perunConfig)
            log.info(f"Rank {rank}: Subprocess: Processed data node: {hostNode}")
            # This should send a single processed node for the current computational node
            queue.put(hostNode, block=True)
            log.info(f"Rank {rank}: Subprocess: Sent data")

            # Reset
            timesteps = []
            rawValues = []
            for _ in lSensors:
                rawValues.append([])
        elif close_event.is_set():
            monitoring = False
        else:
            time.sleep(sampling_period / 2)

    log.info("Close event recived.")

    # Close backends
    for backend in backends:
        log.debug(f"Closing backend {backend}")
        del backend

    # Close live callbacks
    for callback in live_callback_inits.values():
        log.debug(f"Closing callback {callback}")
        del callback
    return
