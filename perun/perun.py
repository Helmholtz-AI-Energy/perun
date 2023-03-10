"""Core perun functionality."""
import platform

# import sys
import time
import types
from datetime import datetime
from functools import reduce
from multiprocessing import Event, Process, Queue
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Union

import numpy as np

from perun import COMM_WORLD, log
from perun.backend import Backend, Sensor, backends
from perun.comm import Comm
from perun.configuration import config
from perun.coordination import assignSensors
from perun.data_model.data import DataNode, NodeType, RawData
from perun.data_model.measurement_type import Magnitude, MetricMetaData, Unit
from perun.data_model.sensor import DeviceType
from perun.io.io import IOFormat, exportTo
from perun.processing import processDataNode, processSensorData
from perun.util import getRunId, getRunName

# from perun.processing import postprocessing
# from perun.report import report


def getSensorConfiguration(comm: Comm, backends: List[Backend]) -> Set[str]:
    """
    Obtain a list with the assigned devices to the current rank.

    Args:
        comm (Comm): MPI communicator object
        backends (List[Backend]): List of available backend objects

    Returns:
        List[str]: IDs of assigned devices to the current rank
    """
    visibleSensors: Set[str] = reduce(
        lambda a, b: a | b, [backend.visibleSensors() for backend in backends]
    )

    log.debug(f"Rank {comm.Get_rank()} : Visible devices {visibleSensors}")
    globalVisibleSensors = comm.allgather(visibleSensors)
    globalHostnames = comm.allgather(platform.node())

    globalVisibleSensors = assignSensors(globalVisibleSensors, globalHostnames)

    return globalVisibleSensors[comm.Get_rank()]


def monitor_application(
    app: Union[Path, Callable], app_args: tuple = tuple(), app_kwargs: dict = dict()
) -> Optional[Any]:
    """Execute coordination, monitoring, post-processing, and reporting steps, in that order.

    Raises:
        executionError: From cmd line execution, raises any error found on the monitored app.
        functionError:  From decorator execution, raises any error found on the monitored method.

    Returns:
        Optional[Any]: In decorator mode, return the output of the decorated method.
    """
    # outPath: Path = Path(config.get("output", "data_out"))

    # Get node devices
    log.debug(f"Backends: {backends}")
    lSensorIds: Set[str] = getSensorConfiguration(COMM_WORLD, backends)

    for backend in backends:
        backend.close()

    log.debug(f"Rank {COMM_WORLD.Get_rank()} - lSensorIds : {lSensorIds}")

    start_event = Event()
    stop_event = Event()

    queue: Optional[Queue] = None
    perunSP: Optional[Process] = None
    # If assigned devices, start subprocess
    if len(lSensorIds) > 0:
        queue = Queue()
        perunSP = Process(
            target=perunSubprocess,
            args=[
                queue,
                start_event,
                stop_event,
                lSensorIds,
                config.getfloat("monitor", "frequency"),
            ],
        )
        perunSP.start()

    app_result: Optional[Any] = None
    COMM_WORLD.barrier()
    start = datetime.now()

    if isinstance(app, Path):
        # filePath = app
        try:
            with open(str(app), "r") as scriptFile:
                start_event.set()
                exec(
                    scriptFile.read(),
                    {"__name__": "__main__", "__file__": app.name},
                )
                stop_event.set()
        except Exception as e:
            log.error(f"Found error on monitored script: {str(app)}")
            stop_event.set()
            raise e

    elif isinstance(app, types.FunctionType):
        # filePath = Path(sys.argv[0])
        start_event.set()
        try:
            app_result = app(*app_args, **app_kwargs)
        except Exception as e:
            stop_event.set()
            raise e
        stop_event.set()

    log.debug("Set closed event")
    # stop = datetime.now()

    # nodeData: Optional[DataNode]
    # Obtain perun subprocess results
    if queue and perunSP:
        log.debug("Getting queue contents")
        nodeData = queue.get(block=True)
        log.debug("Got queue contents")
        log.debug("Waiting for subprocess to close")
        perunSP.join()
        perunSP.close()
        log.debug("Subprocess closed")
        queue.close()
    else:
        nodeData = None

    # Sync
    COMM_WORLD.barrier()
    log.debug("Everyone exited the subprocess")

    # Collect data from everyone on the first rank
    dataNodes: Optional[List[DataNode]] = COMM_WORLD.gather(nodeData, root=0)
    if dataNodes:
        runNode = DataNode(
            id=getRunId(start),
            type=NodeType.RUN,
            metadata={
                "app_name": getRunName(app),
                "startime": start.isoformat(),
            },
            nodes={node.id: node for node in dataNodes if node},
        )
        runNode = processDataNode(runNode)

        data_out = Path(config.get("output", "data_out"))
        format = IOFormat(config.get("output", "format"))
        includeRawData = config.getboolean("output", "raw")
        depth = NodeType(config.getint("output", "depth"))
        exportTo(data_out, runNode, format, includeRawData, depth)

    return app_result


def perunSubprocess(
    queue: Queue, start_event, stop_event, deviceIds: Set[str], frequency: float
):
    """
    Parallel function that samples energy values from hardware libraries.

    Args:
        queue (Queue): multiprocessing Queue object where the results are sent after finish
        start_event (_type_): Marks that perun finished setting up and started sampling from devices
        stop_event (_type_): Signal the subprocess that the monitored processed has finished
        deviceIds (Set[str]): List of device ids to sample from
        frequency (int): Sampling frequency in Hz
    """
    from perun.backend import backends

    lSensors: List[Sensor] = []
    for backend in backends:
        backend.setup()
        lSensors += backend.getSensors(deviceIds)

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

    log.debug(f"perunSP lSensors: {lSensors}")

    start_event.wait()
    timesteps.append(time.time_ns())
    for idx, device in enumerate(lSensors):
        rawValues[idx].append(device.read())

    while not stop_event.wait(1.0 / frequency):
        timesteps.append(time.time_ns())
        for idx, device in enumerate(lSensors):
            rawValues[idx].append(device.read())

    log.debug("Subprocess: Stop event received.")
    for backend in backends:
        backend.close()

    log.debug("Subprocess: Closed backends")
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

    log.debug("Subprocess: Preprocessed Sensor Data")
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

            dn = processDataNode(dn)
            deviceGroupNodes.append(dn)
        else:
            deviceGroupNodes.extend(sensorNodes)

    log.debug("Subprocess: Preprocessed Device Data")

    hostNode = DataNode(
        id=platform.node(),
        type=NodeType.NODE,
        metadata={},
        nodes={node.id: node for node in deviceGroupNodes},
    )
    processDataNode(hostNode)

    # This should send a single processed node for the current computational node
    queue.put(hostNode, block=True)
    log.debug("Subprocess: Sent data")
