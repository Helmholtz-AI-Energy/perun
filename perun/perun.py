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

import h5py
import numpy as np
from mpi4py import MPI

from perun import log
from perun.backend import Backend, Device
from perun.report import report
from perun.storage import ExperimentStorage, LocalStorage
from perun.units import MagnitudePrefix


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


def monitor(
    frequency: float = 1.0,
    outDir: str = "./",
    format: str = "txt",
    horeka: bool = False,
):
    """Decorate function to monitor its energy usage."""

    def inner_function(func):
        @functools.wraps(func)
        def func_wrapper(*args, **kwargs):

            from perun.backend import backends

            comm = MPI.COMM_WORLD
            start_event = Event()
            stop_event = Event()

            filePath: Path = Path(sys.argv[0])
            outPath: Path = Path(outDir)

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
                    args=[queue, start_event, stop_event, lDeviceIds, frequency],
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

            if comm.rank == 0:
                if not outPath.exists():
                    outPath.mkdir(parents=True)

            scriptName = filePath.name.replace(filePath.suffix, "")
            resultPath = outPath / f"{scriptName}.hdf5"
            log.debug(f"Result path: {resultPath}")
            expStrg = ExperimentStorage(resultPath, comm)
            if lStrg:
                log.debug("Creating new experiment")
                expId = expStrg.addExperimentRun(lStrg.toDict())
                expStrg.saveDeviceData(expId, lStrg)

                if horeka:
                    from perun.extras.horeka import get_horeka_measurements

                    get_horeka_measurements(
                        comm, outPath, expStrg.experimentName, expId, start, stop
                    )
            else:
                expId = expStrg.addExperimentRun(None)

            # Post post-process
            comm.barrier()
            postprocessing(expStorage=expStrg)
            comm.barrier()
            if comm.rank == 0:
                print(report(expStrg, expIdx=expId, format=format))
            comm.barrier()
            expStrg.close()

        return func_wrapper

    return inner_function


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

    for backend in backends:
        backend.close()

    queue.put(lStrg)


def postprocessing(expStorage: ExperimentStorage):
    """Process the obtained data."""
    expRuns = expStorage.getExperimentRuns()
    totalExpEnergy_kJ = 0
    totalExpRuntime_s = 0
    for run in expRuns:
        if "totalRunEnergy_kJ" not in run.attrs:
            _postprocessRun(run)
        totalExpEnergy_kJ += run.attrs["totalRunEnergy_kJ"]
        totalExpRuntime_s += run.attrs["totalRunRuntime_s"]

    rootExp = expStorage.getRootObject()
    rootExp.attrs["totalExpEnergy_kJ"] = totalExpEnergy_kJ
    rootExp.attrs["totalExpRuntime_s"] = totalExpRuntime_s


def _postprocessRun(run: h5py.Group):
    """
    Collect run statistics and save them in the group.

    Args:
        run (h5py.Group): Run hdf5 group
    """
    totalRunEnergy_kJ = 0
    totalRunRuntime_s = 0
    runAvgPower_kW = 0
    totalRunRuntime_s = 0

    for node in run.values():
        if "totalNodeEnergy_kJ" not in node.attrs:
            _postprocessNode(node)
        totalRunEnergy_kJ += node.attrs["totalNodeEnergy_kJ"]
        runAvgPower_kW += node.attrs["avgNodePower_kW"]
        totalRunRuntime_s = max(totalRunRuntime_s, node.attrs["totalNodeRuntime_s"])

    run.attrs["totalRunEnergy_kJ"] = totalRunEnergy_kJ
    run.attrs["totalRunRuntime_s"] = totalRunRuntime_s
    run.attrs["runAvgPower_kW"] = runAvgPower_kW


def _postprocessNode(node: h5py.Group):
    """
    Collect node statistics and save them in the group.

    Args:
        node (h5py.Group): Node hdf5 group
    """
    totalNodeEnergy_kJ = 0
    avgNodePower_kW = 0
    t_ns_ds: h5py.Dataset = node["t_ns"]

    mag = t_ns_ds.attrs["mag"]
    transformFactor = MagnitudePrefix.transformFactor(mag, "")
    node.attrs["totalNodeRuntime_s"] = (t_ns_ds[-1] - t_ns_ds[0]) * transformFactor

    for device in node.values():
        if "/t_ns" not in device.name:
            if "totalDeviceEnergy_kJ" not in device.attrs:
                _postprocessDevice(device, t_ns_ds)
            totalNodeEnergy_kJ += device.attrs["totalDeviceEnergy_kJ"]
            avgNodePower_kW += device.attrs["avgDevicePower_kW"]

    node.attrs["totalNodeEnergy_kJ"] = totalNodeEnergy_kJ
    node.attrs["avgNodePower_kW"] = avgNodePower_kW


def _postprocessDevice(device: h5py.Dataset, t_ns: h5py.Dataset):
    """
    Process device raw data and gather report statistics.

    Args:
        device (h5py.Dataset): Device hdf5 dataset
        t_ns (h5py.Dataset): Timesteps hdf5 dataset
    """
    mag = device.attrs["scale_prefix"]
    mTransFactor = MagnitudePrefix.transformFactor(mag, "kilo")
    tTransFactor = MagnitudePrefix.transformFactor(t_ns.attrs["mag"], "")

    if device.attrs["units"] == "Joule":
        energy_array = device[:]
        maxValue = device.attrs["valid_max"]
        d_energy = energy_array[1:] - energy_array[:-1]
        d_energy[d_energy <= 0] = d_energy[d_energy <= 0] + maxValue
        total_energy = d_energy.sum()

        totalDeviceEnergy_kJ = float(total_energy) * mTransFactor
        device.attrs["totalDeviceEnergy_kJ"] = totalDeviceEnergy_kJ
        device.attrs["avgDevicePower_kW"] = totalDeviceEnergy_kJ / (
            (t_ns[-1] - t_ns[0]) * tTransFactor
        )
    elif device.attrs["units"] == "Watt":
        power_v = device[:] * mTransFactor
        t = t_ns[:] * tTransFactor
        energy_v = np.diff(t) * (power_v[:-1] + power_v[1:]) / 1
        energy_v = np.cumsum(energy_v)
        device.attrs["totalDeviceEnergy_kJ"] = energy_v[-1]
        device.attrs["avgDevicePower_kW"] = np.mean(power_v)
