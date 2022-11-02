import h5py
import numpy as np

from perun.configuration import config
from perun.storage import ExperimentStorage
from perun.units import Joule, MagnitudePrefix


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
