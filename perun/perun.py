"""Core perun functionality."""
from datetime import datetime
from functools import reduce
import functools
from pathlib import Path
import platform
from typing import Optional
from perun.backend import Backend, Device
from perun.storage import LocalStorage
from perun import log
from multiprocessing import Event, Process, Queue
from mpi4py import MPI
import perun
import sys


def getDeviceConfiguration(comm: MPI.Comm, backends: list[Backend]) -> list[str]:
    """
    Obtain a list with the assigned devices to the current rank.

    Args:
        comm (Comm): MPI communicator object
        backends (list[Backend]): List of available backend objects

    Returns:
        list[str]: IDs of assigned devices to the current rank
    """
    visibleDevices: set[str] = reduce(
        lambda a, b: a | b, [backend.visibleDevices() for backend in backends]
    )

    log.debug(f"Rank {comm.rank} : Visible devices {visibleDevices}")
    globalDeviceNames = comm.allgather(visibleDevices)
    globalHostnames = comm.allgather(platform.node())

    previousHosts = {}
    for index, (hostname, globalDevices) in enumerate(
        zip(globalHostnames, globalDeviceNames)
    ):
        if hostname not in previousHosts:
            previousHosts[hostname] = index
        else:
            prevIndex = previousHosts[hostname]
            globalDeviceNames[prevIndex] |= globalDevices
            globalDeviceNames[index] = set()

    return globalDeviceNames[comm.rank]


def monitor(frequency: int = 1, outDir: str = "./"):
    """Decorate function to monitor its energy usage."""

    def inner_function(func):
        @functools.wraps(func)
        def func_wrapper(*args, **kwargs):

            comm = MPI.COMM_WORLD
            start_event = Event()
            stop_event = Event()

            filePath: Path = Path(sys.argv[0])
            outPath: Path = Path(outDir)

            # Get node devices
            log.debug(f"Backends: {perun.backends}")
            lDeviceIds: list[str] = perun.getDeviceConfiguration(comm, perun.backends)

            for backend in perun.backends:
                backend.close()

            log.debug(f"Rank {comm.rank} - lDeviceIds : {lDeviceIds}")

            # If assigned devices, start subprocess
            if len(lDeviceIds) > 0:
                queue: Queue = Queue()
                perunSP = Process(
                    target=perun.perunSubprocess,
                    args=[queue, start_event, stop_event, lDeviceIds, frequency],
                )
                perunSP.start()
                start_event.wait()

            # Sync everyone
            comm.barrier()

            func(*args, **kwargs)
            stop_event.set()

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

            if comm.rank == 0:
                if not outPath.exists():
                    outPath.mkdir(parents=True)

            scriptName = filePath.name.removesuffix(filePath.suffix)
            resultPath = outPath / f"{scriptName}.hdf5"
            log.debug(f"Result path: {resultPath}")
            expStrg = perun.ExperimentStorage(resultPath, comm)
            if lStrg:
                log.debug("Creating new experiment")
                expId = expStrg.addExperimentRun(lStrg.toDict())
                expStrg.saveDeviceData(expId, lStrg)
            else:
                expId = expStrg.addExperimentRun(None)

            expStrg.close()

        return func_wrapper

    return inner_function


def perunSubprocess(
    queue: Queue, start_event, stop_event, deviceIds: set[str], frequency: int
):
    """
    Parallel function that samples energy values from hardware libraries.

    Args:
        queue (Queue): multiprocessing Queue object where the results are sent after finish
        start_event (_type_): Marks that perun finished setting up and started sampling from devices
        stop_event (_type_): Signal the subprocess that the monitored processed has finished
        deviceIds (set[str]): List of device ids to sample from
        frequency (int): Sampling frequency in Hz
    """
    from perun import backends

    lDevices: list[Device] = []
    for backend in backends:
        backend.setup()
        lDevices += backend.getDevices(deviceIds)

    log.debug(f"Perun SP lDevices: {lDevices}")
    lStrg = LocalStorage(platform.node(), lDevices)
    start_event.set()

    while not stop_event.wait(1.0 / frequency):
        ts = datetime.now().timestamp()
        stepData = {}
        for device in lDevices:
            stepData[device.id] = device.read()
        lStrg.addTimestep(ts, stepData)

    for backend in backends:
        backend.close()

    queue.put(lStrg)


def postprocessing():
    """Process the obtained data."""
    pass
