"""Storage Module."""
from pathlib import Path
from typing import Any, Union
from perun.backend.device import Device
from perun.units import MagnitudePrefix
from datetime import datetime
import h5py
from h5py import Group
from mpi4py.MPI import Comm


class LocalStorage:
    """Object used to store device data inside the perunSubprocess."""

    def __init__(self, nodeName: str, devices: list[Device]):
        """Create dictionary based on nodeName and devices."""
        self.devices = [device.toDict() for device in devices]
        self.nodeName = nodeName
        self.nodeData: dict[str, list[Any]] = {"ts": []}
        for device in self.devices:
            self.nodeData[device["id"]] = []

    def addTimestep(self, timestamp: float, step: dict):
        """Add one step of information to storage."""
        self.nodeData["ts"].append(timestamp)
        for key, value in step.items():
            self.nodeData[key].append(value)

    def toDict(self) -> dict[str, Any]:
        """Lightweight local storage without the data."""
        return {
            "devices": self.devices,
            "nodeName": self.nodeName,
            "steps": len(self.nodeData["ts"]),
        }


class ExperimentStorage:
    """Store hardware measurments across multiple runs of the same experiment."""

    def __init__(self, filePath: Path, comm: Comm):
        """Initialize experiment storage."""
        self.comm = comm
        if self.comm.size > 1:
            self.file = h5py.File(filePath, "a", driver="mpio", comm=self.comm)
        else:
            self.file = h5py.File(filePath, "a")

        self.experimentName = self._getExperimentName(filePath)

        if self.experimentName not in self.file:
            rootGroup = self.file.create_group(self.experimentName)
            rootGroup.attrs["creation_date"] = str(datetime.utcnow())

    def _getExperimentName(self, filePath: Path) -> str:
        """Remove suffix from a file path."""
        return filePath.name.replace(filePath.suffix, "")

    def addExperimentRun(self, lStrg: Union[dict, None]) -> int:
        """Add new experiment group and setup the internal datasets."""
        expIdx: int = len(self.file[self.experimentName].keys())
        expGroup = self.file[self.experimentName].create_group(f"exp_{expIdx}")
        expGroup.attrs["experiment_date"] = str(datetime.utcnow())

        gatherdStrg: list[Union[dict, None]] = self.comm.allgather(lStrg)

        for strg in gatherdStrg:
            if strg:
                self._createNodeDataStrg(expGroup, strg)

        return expIdx

    def saveDeviceData(self, expId: int, lStrg: LocalStorage):
        """
        Write the device data on the newly created hdf5 datasets.

        Args:
            expId (int): id of the current experiment run
            lStrg (LocalStorage): Storage with hardware measurements
        """
        group = self.file[self.experimentName][f"exp_{expId}"][lStrg.nodeName]
        group["ts"][:] = lStrg.nodeData["ts"]

        for device in lStrg.devices:
            dsId = self._dsFromDevice(device)
            group[dsId][:] = lStrg.nodeData[device["id"]]

    def _createNodeDataStrg(self, group: Group, strg: dict):
        """
        Create datasets for a mpi node.

        Args:
            group (Group): Parent hdf5 group
            strg (dict): Dictionary with node and device data
        """
        nodeGroup = group.create_group(strg["nodeName"])
        self._createTimestampDatabase(nodeGroup, strg)
        for device in strg["devices"]:
            self._createDataset(nodeGroup, device, strg["steps"])

    def _createTimestampDatabase(self, group: Group, strg: dict):
        """Initilize timestamp database."""
        ts_ds: h5py.Dataset = group.create_dataset(name="ts", shape=(strg["steps"],))
        ts_ds.attrs["long_name"] = "timestamp"
        ts_ds.attrs["units"] = "seconds"
        ts_ds.attrs["standard_name"] = "timestamp"

    def _createDataset(self, group: Group, deviceDict: dict[str, Any], steps: int):
        """Create a dataset based on node name and device information."""
        ds: h5py.Dataset = group.create_dataset(
            self._dsFromDevice(deviceDict), shape=(steps,)
        )
        ds.attrs["long_name"] = deviceDict["long_name"]
        ds.attrs["units"] = deviceDict["unit"].name
        ds.attrs["symbol"] = deviceDict["unit"].symbol
        ds.attrs.create("coordinates", data=["ts"])
        ds.attrs.create("valid_min", data=deviceDict["unit"].min_value, dtype="f")
        ds.attrs.create("valid_max", data=deviceDict["unit"].max_value, dtype="f")
        ds.attrs.create("_FillValue", data=-1.0, dtype="f")
        ds.attrs.create(
            "scale_factor", data=MagnitudePrefix.getFactor(deviceDict["mag"]), dtype="f"
        )
        ds.attrs["scale_prefix"] = deviceDict["mag"]
        ds.attrs.create("add_offset", data=1.0, dtype="f")

    def _dsFromDevice(self, device: dict[str, Any]) -> str:
        """
        Generate dataset name from device dict.

        Args:
            device (dict[str, any]): Device dict.

        Returns:
            str: Dataset name string.
        """
        prefixSym = MagnitudePrefix.getSymbol(device["mag"])
        return f"{device['id']}_{prefixSym}{device['unit'].symbol}"

    def close(self):
        """Close hdf5 file."""
        self.file.close()
