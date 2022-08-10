"""Core perun functionality."""
from datetime import datetime
from functools import reduce
from mpi4py.MPI import Comm
import platform
from perun.backend import Backend, Device
from perun.storage import LocalStorage
from perun import log
from multiprocessing import Queue


def getDeviceConfiguration(comm: Comm, backends: list[Backend]) -> list[str]:
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
