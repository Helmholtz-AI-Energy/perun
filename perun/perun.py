"""Core perun functionality."""
import functools
import platform
import sys
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
from perun.configuration import config, read_custom_config, save_to_config
from perun.coordination import assignSensors
from perun.data_model.data import DataNode, NodeType, RawData
from perun.data_model.measurement_type import Magnitude, MeasurementType, Unit

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
    outPath: Path = Path(config.get("output", "data_out"))

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
        filePath = app
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
        filePath = Path(sys.argv[0])
        start_event.set()
        try:
            app_result = app(*app_args, **app_kwargs)
        except Exception as e:
            stop_event.set()
            raise e
        stop_event.set()

    log.debug("Set closed event")
    stop = datetime.now()

    lStrg: Optional[DataNode]
    # Obtain perun subprocess results
    if queue and perunSP:
        log.debug("Getting queue contents")
        lStrg = queue.get(block=True)
        log.debug("Got queue contents")
        log.debug("Waiting for subprocess to close")
        perunSP.join()
        perunSP.close()
        log.debug("Subprocess closed")
        queue.close()
    else:
        lStrg = None

    # Sync
    COMM_WORLD.barrier()
    log.debug("Passed first barrier")

    # Save raw data to hdf5
    save_data(COMM_WORLD, outPath, filePath, lStrg, start, stop)
    return app_result


def monitor(
    configuration: str = "./.perun.ini",
    **conf_kwargs,
):
    """Decorate function to monitor its energy usage."""

    def inner_function(func):
        @functools.wraps(func)
        def func_wrapper(*args, **kwargs):
            # Get custom config and kwargs

            read_custom_config(None, None, configuration)
            for key, value in conf_kwargs.items():
                save_to_config(key, value)

            log.setLevel(config.get("debug", "log_lvl"))
            func_result = monitor_application(func, args, kwargs)

            return func_result

        return func_wrapper

    return inner_function


def save_data(
    comm: Comm,
    outPath: Path,
    filePath: Path,
    lStrg: Optional[DataNode],
    start: datetime,
    stop: datetime,
):
    """
    Save subprocess data in the locations defined on the configuration.

    Args:
        comm (Comm): Communication Object
        outPath (Path): Result path
        filePath (Path): HDF5 path
        lStrg (Optional[LocalStorage]): LocalStorage object (if available)
        start (datetime): Start time of the run
        stop (datetime): Stop time of the run
    """
    if comm.Get_rank() == 0:
        if not outPath.exists():
            outPath.mkdir(parents=True)

    scriptName = filePath.name.replace(filePath.suffix, "")
    resultPath = outPath / f"{scriptName}.hdf5"
    log.debug(f"Result path: {resultPath}")

    # expStrg = ExperimentStorage(resultPath, comm, write=True) */
    # expId = expStrg.addExperimentRun(lStrg)
    # if lStrg and config.getboolean("horeka", "enabled"):
    #     try:
    #         from perun.extras.horeka import get_horeka_measurements
    #
    #         get_horeka_measurements(
    #             comm, outPath, expStrg.experimentName, expId, start, stop
    #         )
    #     except Exception as E:
    #         log.error("Failed to get influxdb data from horeka")
    #         log.error(E)
    #
    # # Post post-process
    # comm.barrier()
    # postprocessing(expStorage=expStrg)
    # if comm.Get_rank() == 0:
    #     print(report(expStrg, expIdx=expId, format=config.get("output", "format")))
    # comm.barrier()
    # expStrg.close()


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
    t_mT = MeasurementType(
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

    while not stop_event.wait(1.0 / frequency):
        timesteps.append(np.float32(time.time()))
        for idx, device in enumerate(lSensors):
            rawValues[idx].append(device.read())

    log.debug("Subprocess: Stop event received.")
    for backend in backends:
        backend.close()

    log.debug("Subprocess: Closed backends")
    deviceNodes: Dict = {}
    t_s = np.array(timesteps)
    for sensor, values in zip(lSensors, rawValues):
        if sensor.type not in deviceNodes:
            deviceNodes[sensor.type] = []

        dn = DataNode(
            sensor.id,
            NodeType.SENSOR,
            sensor.metadata,
            deviceType=sensor.type,
            raw_data=RawData(t_s, np.array(values), t_mT, sensor.dataType),
        )
        # Apply processing to sensor node
        deviceNodes[sensor.type].append(dn)

    log.debug("Subprocess: Preprocessed Device Data")

    # This should send a single processed node for the current computational node
    queue.put(deviceNodes, block=True)
    log.debug("Subprocess: Sent lStrg")
