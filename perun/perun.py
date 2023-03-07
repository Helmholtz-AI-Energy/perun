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
from typing import Any, Callable, List, Optional, Set, Union

import numpy as np

from perun import COMM_WORLD, log
from perun.backend import Backend, Device, backends
from perun.comm import Comm
from perun.configuration import config, read_custom_config, save_to_config
from perun.processing import postprocessing
from perun.report import report
from perun.storage import ExperimentStorage, LocalStorage


def getDeviceConfiguration(comm: Comm, backends: List[Backend]) -> Set[str]:
    """
    Obtain a list with the assigned devices to the current rank.

    Args:
        comm (Comm): MPI communicator object
        backends (List[Backend]): List of available backend objects

    Returns:
        List[str]: IDs of assigned devices to the current rank
    """
    visibleDevices: Set[str] = reduce(
        lambda a, b: a | b, [backend.visibleDevices() for backend in backends]
    )

    log.debug(f"Rank {comm.Get_rank()} : Visible devices {visibleDevices}")
    globalVisibleDevices = comm.allgather(visibleDevices)
    globalHostnames = comm.allgather(platform.node())

    globalVisibleDevices = assignDevices(globalVisibleDevices, globalHostnames)

    return globalVisibleDevices[comm.Get_rank()]


def assignDevices(hostDevices: List[Set[str]], hostNames: List[str]) -> List[Set[str]]:
    """Assign found devices to the lowest rank in each host.

    Args:
        hostDevices (List[Set[str]]): List with lenght of the mpi world size, with each index containing the devices of each rank.
        hostNames (List[str]): Hostname of the mpi rank at the index.

    Returns:
        List[Set[str]]: New list with the devices assiged to each rank.
    """
    previousHosts = {}
    for index, (name, devices) in enumerate(zip(hostNames, hostDevices)):
        if name not in previousHosts:
            previousHosts[name] = index
        else:
            prevIndex = previousHosts[name]
            hostDevices[prevIndex] |= devices
            hostDevices[index] = set()
    return hostDevices


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
    lDeviceIds: Set[str] = getDeviceConfiguration(COMM_WORLD, backends)

    for backend in backends:
        backend.close()

    log.debug(f"Rank {COMM_WORLD.Get_rank()} - lDeviceIds : {lDeviceIds}")

    start_event = Event()
    stop_event = Event()

    queue: Optional[Queue] = None
    perunSP: Optional[Process] = None
    # If assigned devices, start subprocess
    if len(lDeviceIds) > 0:
        queue = Queue()
        perunSP = Process(
            target=perunSubprocess,
            args=[
                queue,
                start_event,
                stop_event,
                lDeviceIds,
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

    lStrg: Optional[LocalStorage]
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
    lStrg: Optional[LocalStorage],
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
    expStrg = ExperimentStorage(resultPath, comm, write=True)
    expId = expStrg.addExperimentRun(lStrg)
    if lStrg and config.getboolean("horeka", "enabled"):
        try:
            from perun.extras.horeka import get_horeka_measurements

            get_horeka_measurements(
                comm, outPath, expStrg.experimentName, expId, start, stop
            )
        except Exception as E:
            log.error("Failed to get influxdb data from horeka")
            log.error(E)

    # Post post-process
    comm.barrier()
    postprocessing(expStorage=expStrg)
    if comm.Get_rank() == 0:
        print(report(expStrg, expIdx=expId, format=config.get("output", "format")))
    comm.barrier()
    expStrg.close()


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

    lDevices: List[Device] = []
    for backend in backends:
        backend.setup()
        lDevices += backend.getDevices(deviceIds)

    log.debug(f"Perun SP lDevices: {lDevices}")
    lStrg = LocalStorage(platform.node(), lDevices)
    start_event.wait()

    while not stop_event.wait(1.0 / frequency):
        t = np.uint64(time.time_ns())
        stepData = {}
        for device in lDevices:
            stepData[device.id] = device.read()
        lStrg.addTimestep(t, stepData)

    log.debug("Subprocess: Stop event received.")
    for backend in backends:
        backend.close()
    log.debug("Subprocess: Closed backends")

    queue.put(lStrg, block=True)
    log.debug("Subprocess: Sent lStrg")
