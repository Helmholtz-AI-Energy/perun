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
from perun.backend import Backend, Device, backends
from perun.configuration import config, read_custom_config, save_to_config
from perun.report import report
from perun.storage import ExperimentStorage, LocalStorage
from perun.units import Joule, MagnitudePrefix


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

            if comm.rank == 0:
                if not outPath.exists():
                    outPath.mkdir(parents=True)

            scriptName = filePath.name.replace(filePath.suffix, "")
            resultPath = outPath / f"{scriptName}.hdf5"
            log.debug(f"Result path: {resultPath}")
            expStrg = ExperimentStorage(resultPath, comm, write=True)
            expId = expStrg.addExperimentRun(lStrg)
            if lStrg and config.getboolean("horeka", "enabled"):
                from perun.extras.horeka import get_horeka_measurements

                get_horeka_measurements(
                    comm, outPath, expStrg.experimentName, expId, start, stop
                )

            # Post post-process
            comm.barrier()
            postprocessing(expStorage=expStrg)
            if comm.rank == 0:
                print(
                    report(expStrg, expIdx=expId, format=config.get("report", "format"))
                )
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

    log.debug("Subprocess: Stop event received.")
    for backend in backends:
        backend.close()
    log.debug("Subprocess: Closed backends")

    queue.put(lStrg, block=True)
    log.debug("Subprocess: Sent lStrg")


def postprocessing(expStorage: ExperimentStorage, reset: bool = False):
    """Process the obtained data."""
    if (expStorage.serial and expStorage.comm.rank == 0) or not expStorage.serial:
        expRuns = expStorage.getExperimentRuns()
        totalExpEnergy_kWh = 0
        totalExpRuntime_s = 0
        totalExpCO2e_kg = 0
        totalExpPrice_euro = 0
        for run in expRuns:
            if "totalRunEnergy_kWh" not in run.attrs or reset:
                _postprocessRun(run, reset)
            totalExpEnergy_kWh += run.attrs["totalRunEnergy_kWh"]
            totalExpRuntime_s += run.attrs["totalRunRuntime_s"]
            totalExpCO2e_kg += run.attrs["totalRunCO2e_kg"]
            totalExpPrice_euro += run.attrs["totalRunPrice_euro"]

        rootExp = expStorage.getRootObject()
        rootExp.attrs["totalExpEnergy_kWh"] = totalExpEnergy_kWh
        rootExp.attrs["totalExpRuntime_s"] = totalExpRuntime_s
        rootExp.attrs["totalExpCO2e_kg"] = totalExpCO2e_kg
        rootExp.attrs["totalExpPrice_euro"] = totalExpPrice_euro


def _postprocessRun(run: h5py.Group, reset: bool = False):
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
        if "totalNodeEnergy_kJ" not in node.attrs or reset:
            _postprocessNode(node, reset)
        totalRunEnergy_kJ += node.attrs["totalNodeEnergy_kJ"]
        runAvgPower_kW += node.attrs["avgNodePower_kW"]
        totalRunRuntime_s = max(totalRunRuntime_s, node.attrs["totalNodeRuntime_s"])

    totalRunEnergy_kWh = Joule.to_kWh(
        totalRunEnergy_kJ * MagnitudePrefix.transformFactor("kilo", "")
    ) * config.getfloat("report", "pue")
    run.attrs["totalRunEnergy_kWh"] = totalRunEnergy_kWh
    run.attrs["totalRunRuntime_s"] = totalRunRuntime_s
    run.attrs["runAvgPower_kW"] = runAvgPower_kW

    run.attrs["totalRunCO2e_kg"] = totalRunEnergy_kWh * config.getfloat(
        "report", "emissions-factor"
    )
    run.attrs["totalRunPrice_euro"] = (
        totalRunEnergy_kWh * config.getfloat("report", "price-factor") / 100
    )


def _postprocessNode(node: h5py.Group, reset: bool = False):
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
        if "/t_ns" not in device.name and device.attrs["units"] in ["Joule", "Watt"]:
            if "totalDeviceEnergy_kJ" not in device.attrs or reset:
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
        dtype = device.dtype.name
        d_energy = energy_array[1:] - energy_array[:-1]
        if "uint" in dtype:
            idx = d_energy >= maxValue
            max_dtype = np.iinfo(dtype).max
            d_energy[idx] = maxValue + d_energy[idx] - max_dtype
        else:
            idx = d_energy <= 0
            d_energy[idx] = d_energy[idx] + maxValue
        total_energy = d_energy.sum()

        totalDeviceEnergy_kJ = float(total_energy) * mTransFactor
        device.attrs["totalDeviceEnergy_kJ"] = totalDeviceEnergy_kJ
        device.attrs["avgDevicePower_kW"] = totalDeviceEnergy_kJ / (
            (t_ns[-1] - t_ns[0]) * tTransFactor
        )
    elif device.attrs["units"] == "Watt":
        power_w = device[:] * mTransFactor
        t_s = t_ns[:] * tTransFactor
        energy_kj = np.trapz(power_w, t_s)
        device.attrs["totalDeviceEnergy_kJ"] = energy_kj
        device.attrs["avgDevicePower_kW"] = np.mean(power_w)
