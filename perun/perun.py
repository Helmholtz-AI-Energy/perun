"""Core perun functionality."""
import functools
import platform
import sys
import time
from datetime import datetime
from functools import reduce
from multiprocessing import Event, Process, Queue
from pathlib import Path
from typing import List, Optional, Set

import numpy as np
from mpi4py import MPI

from perun import log
from perun.backend import Backend, Device, backends
from perun.configuration import config, read_custom_config, save_to_config
from perun.processing import postprocessing
from perun.report import report
from perun.storage import ExperimentStorage, LocalStorage


def getDeviceConfiguration(comm: MPI.Comm, backends: List[Backend]) -> List[str]:
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

    log.debug(f"Rank {comm.rank} : Visible devices {visibleDevices}")
    globalVisibleDevices = comm.allgather(visibleDevices)
    globalHostnames = comm.allgather(platform.node())

    globalVisibleDevices = assignDevices(globalVisibleDevices, globalHostnames)

    return globalVisibleDevices[comm.rank]


def assignDevices(hostDevices: List[Set[str]], hostNames: List[str]) -> List[Set[str]]:
    previousHosts = {}
    for index, (name, devices) in enumerate(zip(hostNames, hostDevices)):
        if name not in previousHosts:
            previousHosts[name] = index
        else:
            prevIndex = previousHosts[name]
            hostDevices[prevIndex] |= devices
            hostDevices[index] = set()
    return hostDevices


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

            comm = MPI.COMM_WORLD
            start_event = Event()
            stop_event = Event()

            filePath: Path = Path(sys.argv[0])
            outPath: Path = Path(config.get("monitor", "data_out"))

            # Get node devices
            log.debug(f"Backends: {backends}")
            lDeviceIds: List[str] = getDeviceConfiguration(comm, backends)

            for backend in backends:
                backend.close()

            log.debug(f"Rank {comm.rank} - lDeviceIds : {lDeviceIds}")

            # If assigned devices, start subprocess
            if len(lDeviceIds) > 0:
                queue: Queue = Queue()
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
                start_event.wait()

            # Sync everyone
            comm.barrier()
            start = datetime.now()

            func(*args, **kwargs)
            stop_event.set()
            stop = datetime.now()

            lStrg: Optional[LocalStorage]
            # Obtain perun subprocess results
            if len(lDeviceIds) > 0:
                perunSP.join()
                perunSP.close()
                lStrg = queue.get()
            else:
                lStrg = None

            # Sync
            comm.barrier()

            # Save raw data to hdf5
            save_data(comm, outPath, filePath, lStrg, start, stop)

        return func_wrapper

    return inner_function


def save_data(
    comm: MPI.Comm,
    outPath: Path,
    filePath: Path,
    lStrg: Optional[LocalStorage],
    start: datetime,
    stop: datetime,
):
    """
    Save subprocess data in the locations defined on the configuration.

    Args:
        comm (MPI.Comm): MPI communication object
        outPath (Path): Result path
        filePath (Path): HDF5 path
        lStrg (Optional[LocalStorage]): LocalStorage object (if available)
        start (datetime): Start time of the run
        stop (datetime): Stop time of the run
    """
    if comm.rank == 0:
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
    if comm.rank == 0:
        print(report(expStrg, expIdx=expId, format=config.get("report", "format")))
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
    start_event.set()

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
