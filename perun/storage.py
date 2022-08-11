"""Storage Module."""
from pathlib import Path
from typing import Any, Union
from perun.backend.device import Device
from perun.units import MagnitudePrefix
from datetime import datetime
import h5py
from h5py import Group
from mpi4py.MPI import Comm
import numpy as np


class LocalStorage:
    """Object used to store device data inside the perunSubprocess."""

    def __init__(self, nodeName: str, devices: list[Device]):
        """Create dictionary based on nodeName and devices."""
        self.devices = [device.toDict() for device in devices]
        self.nodeName = nodeName
        self.nodeData: dict[str, list[Any]] = {"t_ns": []}
        for device in self.devices:
            self.nodeData[device["id"]] = []

    def addTimestep(self, timestamp: int, step: dict):
        """Add one step of information to storage."""
        self.nodeData["t_ns"].append(timestamp)
        for key, value in step.items():
            self.nodeData[key].append(value)

    def toDict(self) -> dict[str, Any]:
        """Lightweight local storage without the data."""
        return {
            "devices": self.devices,
            "nodeName": self.nodeName,
            "steps": len(self.nodeData["t_ns"]),
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
        group["t_ns"][:] = np.array(lStrg.nodeData["t_ns"], dtype="float64")

        for device in lStrg.devices:
            dsId = self._dsFromDevice(device)
            group[dsId][:] = np.array(lStrg.nodeData[device["id"]])

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
        t_ns_ds: h5py.Dataset = group.create_dataset(
            name="t_ns", shape=(strg["steps"],), dtype="float64"
        )
        t_ns_ds.attrs["long_name"] = "time"
        t_ns_ds.attrs["units"] = "seconds"
        t_ns_ds.attrs["mag"] = "nano"
        t_ns_ds.attrs["standard_name"] = "time"

    def _createDataset(self, group: Group, deviceDict: dict[str, Any], steps: int):
        """Create a dataset based on node name and device information."""
        ds: h5py.Dataset = group.create_dataset(
            self._dsFromDevice(deviceDict), shape=(steps,), dtype="float64"
        )
        ds.attrs["long_name"] = deviceDict["long_name"]
        ds.attrs["units"] = deviceDict["unit"].name
        ds.attrs["symbol"] = deviceDict["unit"].symbol
        ds.attrs.create("coordinates", data=["t_ns"])
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

    def getExperimentRun(self, index: int) -> Group:
        """
        Return experiment with the desired index.

        Args:
            index (int): Run index

        Returns:
            Group: h5py group with run info
        """
        if index == -1:
            index = len(self.file[self.experimentName].keys())
        return self.file[self.experimentName][f"exp_{index}"]

    def getExperimentRuns(self) -> list[Group]:
        """Return list of run hdf5 groups.

        Returns:
            list[Group]: List of hdf5 groups with run data
        """
        return self.file[self.experimentName].values()

    def getRootObject(self) -> Group:
        """
        Get hdf5 root object.

        Returns:
            Group: Root object
        """
        return self.file[self.experimentName]

    def toDict(self, data: bool = False) -> dict:
        """
        Create dict represation of storage object.

        Args:
            data (bool, optional): Include raw data. Defaults to False.

        Returns:
            dict: Storage dictionary
        """
        rootObj = self.getRootObject()
        expDict: dict[str, Any] = {"name": self.experimentName, "runs": []}
        for key, value in rootObj.attrs.items():
            expDict[key] = str(value)

        for run_id, runs in rootObj.items():
            expDict["runs"].append(self._runToDict(run_id, runs, data))

        return expDict

    def _runToDict(self, name: str, run: Group, data: bool = False) -> dict:
        """
        Get dictionary from run object.

        Args:
            name (str): Run name
            run (Group): Run object
            data (bool, optional): If raw data should be included. Defaults to False.

        Returns:
            dict: run dictionary
        """
        runDict: dict[str, Any] = {"id": name, "node": []}
        for key, value in run.attrs.items():
            runDict[key] = str(value)

        for node_id, node in run.items():
            runDict["node"].append(self._nodeToDict(node_id, node, data))
        return runDict

    def _nodeToDict(self, name: str, node: Group, data: bool = False) -> dict:
        """
        Transform h5py node to dictionary.

        Args:
            name (str): Node name
            node (Group): Node object
            data (bool, optional): If raw data should be included. Defaults to False.

        Returns:
            dict: Node dictionary
        """
        nodeDict: dict[str, Any] = {"id": name, "devices": []}

        for key, value in node.attrs.items():
            nodeDict[key] = str(value)

        for device_id, device in node.items():
            deviceDict: dict[str, Any] = {
                "id": device_id,
            }
            if data:
                deviceDict["data"] = device[:]

            for key, value in device.attrs.items():
                deviceDict[key] = str(value)

            nodeDict["devices"].append(deviceDict)

        return nodeDict
