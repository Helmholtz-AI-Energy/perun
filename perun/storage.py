"""Storage Module."""
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Union

import h5py
import numpy as np
from h5py import Group
from mpi4py.MPI import Comm

from perun import log
from perun.backend.device import Device
from perun.units import MagnitudePrefix


class LocalStorage:
    """Object used to store device data inside the perunSubprocess."""

    def __init__(self, nodeName: str, devices: List[Device]):
        """Create dictionary based on nodeName and devices."""
        self.devices = [device.toDict() for device in devices]
        self.nodeName = nodeName
        self.nodeData: Dict[str, List[np.number]] = {"t_ns": []}
        for device in self.devices:
            self.nodeData[device["id"]] = []

    def addTimestep(self, timestamp: np.uint64, step: dict):
        """Add one step of information to storage."""
        self.nodeData["t_ns"].append(timestamp)
        for key, value in step.items():
            self.nodeData[key].append(value)

    def toDict(self, data=False) -> Dict[str, Any]:
        """Lightweight local storage without the data."""
        returnDict = {
            "devices": self.devices,
            "nodeName": self.nodeName,
            "steps": len(self.nodeData["t_ns"]),
        }
        if data:
            returnDict["nodeData"] = self.nodeData

        return returnDict


class ExperimentStorage:
    """Store hardware measurments across multiple runs of the same experiment."""

    def __init__(self, filePath: Path, comm: Comm, write=False):
        """Initialize experiment storage."""
        self.comm = comm
        self.serial = False
        self.experimentName = self._getExperimentName(filePath)

        # Write new data
        if write:
            if self.comm.size > 1:
                try:
                    self.file = h5py.File(filePath, "a", driver="mpio", comm=self.comm)
                except ValueError as e:
                    log.warn(e)
                    self.serial = True
                    if self.comm.rank == 0:
                        self.file = h5py.File(filePath, "a")
            else:
                self.file = h5py.File(filePath, "a")
        # Only read
        else:
            self.file = h5py.File(filePath, "r")

    def addExperimentRun(self, lStrg: Union[LocalStorage, None]) -> int:
        """Add new experiment group and setup the internal datasets."""
        if self.serial:
            storageDicts = self.comm.allgather(
                lStrg.toDict(data=True) if lStrg else None
            )
            runIdx: Union[int, None] = None
            if self.comm.rank == 0:
                runIdx = self._serialCreate(storageDicts)
            idx: int = self.comm.bcast(runIdx, root=0)
            return idx
        else:
            if self.experimentName not in self.file:
                rootGroup = self.file.create_group(self.experimentName)
                rootGroup.attrs["creation_date"] = str(datetime.utcnow())

            expId = self._addExperimentRun(lStrg)
            if lStrg:
                self._saveDeviceData(expId, lStrg)

            return expId

    def _serialCreate(self, gatheredStrg: List[Union[Dict, None]]) -> int:
        """
        Save device data into hdf5 from a single mpi rank.

        Args:
            filePath (_type_): Path to save directory
            gatheredStrg (List[Union[Dict, None]]): List with device data from all mpi ranks
        """
        if self.experimentName not in self.file:
            rootGroup = self.file.create_group(self.experimentName)
            rootGroup.attrs["creation_date"] = str(datetime.utcnow())

        expIdx: int = len(self.file[self.experimentName].keys())
        expGroup = self.file[self.experimentName].create_group(f"exp_{expIdx}")
        expGroup.attrs["experiment_date"] = str(datetime.utcnow())

        for strg in gatheredStrg:
            if strg:
                self._createNodeDataStrg(expGroup, strg)
                group = self.file[self.experimentName][f"exp_{expIdx}"][
                    strg["nodeName"]
                ]
                group["t_ns"][:] = np.array(strg["nodeData"]["t_ns"], dtype="uint64")

                for device in strg["devices"]:
                    dsId = self._dsFromDevice(device)
                    group[dsId][:] = np.array(strg["nodeData"][device["id"]])
        return expIdx

    def _getExperimentName(self, filePath: Path) -> str:
        """Remove suffix from a file path."""
        return filePath.name.replace(filePath.suffix, "")

    def _addExperimentRun(self, lStrg: Union[LocalStorage, None]) -> int:
        """Add new experiment group and setup the internal datasets."""
        expIdx: int = len(self.file[self.experimentName].keys())
        expGroup = self.file[self.experimentName].create_group(f"exp_{expIdx}")
        expGroup.attrs["experiment_date"] = str(datetime.utcnow())

        gatherdStrg: List[Union[dict, None]] = self.comm.allgather(
            lStrg.toDict() if lStrg else None
        )

        for strg in gatherdStrg:
            if strg:
                self._createNodeDataStrg(expGroup, strg)

        return expIdx

    def _saveDeviceData(self, expId: int, lStrg: LocalStorage):
        """
        Write the device data on the newly created hdf5 datasets.

        Args:
            expId (int): id of the current experiment run
            lStrg (LocalStorage): Storage with hardware measurements
        """
        group = self.file[self.experimentName][f"exp_{expId}"][lStrg.nodeName]
        group["t_ns"][:] = np.array(lStrg.nodeData["t_ns"], dtype="uint64")

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
            name="t_ns", shape=(strg["steps"],), dtype="uint64"
        )
        t_ns_ds.attrs["long_name"] = "time"
        t_ns_ds.attrs["units"] = "seconds"
        t_ns_ds.attrs["mag"] = "nano"
        t_ns_ds.attrs["standard_name"] = "time"

    def _createDataset(self, group: Group, deviceDict: Dict[str, Any], steps: int):
        """Create a dataset based on node name and device information."""
        ds: h5py.Dataset = group.create_dataset(
            self._dsFromDevice(deviceDict), shape=(steps,), dtype=deviceDict["dtype"]
        )
        ds.attrs["long_name"] = deviceDict["long_name"]
        ds.attrs["units"] = deviceDict["unit"].name
        ds.attrs["symbol"] = deviceDict["unit"].symbol
        ds.attrs.create("coordinates", data=["t_ns"])
        ds.attrs.create("valid_min", data=deviceDict["min"], dtype=deviceDict["dtype"])
        ds.attrs.create("valid_max", data=deviceDict["max"], dtype=deviceDict["dtype"])
        ds.attrs.create("_FillValue", data=0.0, dtype=deviceDict["dtype"])
        ds.attrs.create(
            "scale_factor", data=MagnitudePrefix.getFactor(deviceDict["mag"]), dtype="f"
        )
        ds.attrs["scale_prefix"] = deviceDict["mag"]
        ds.attrs.create("add_offset", data=0, dtype=deviceDict["dtype"])

    def _dsFromDevice(self, device: Dict[str, Any]) -> str:
        """
        Generate dataset name from device dict.

        Args:
            device (Dict[str, any]): Device dict.

        Returns:
            str: Dataset name string.
        """
        prefixSym = MagnitudePrefix.getSymbol(device["mag"])
        return f"{device['id']}_{prefixSym}{device['unit'].symbol}"

    def close(self):
        """Close hdf5 file."""
        if (self.serial and self.comm.rank == 0) or not self.serial:
            self.file.close()

    def getLastExperimentIndex(self) -> int:
        """
        Return index of the last experiment in the storage file.

        Returns:
            int: Index of last experiment
        """
        return len(self.file[self.experimentName].keys()) - 1

    def getExperimentRun(self, index: int) -> Group:
        """
        Return experiment with the desired index.

        Args:
            index (int): Run index

        Returns:
            Group: h5py group with run info
        """
        if index == -1:
            index = self.getLastExperimentIndex()
        return self.file[self.experimentName][f"exp_{index}"]

    def getExperimentRuns(self) -> List[Group]:
        """Return list of run hdf5 groups.

        Returns:
            List[Group]: List of hdf5 groups with run data
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
        expDict: Dict[str, Any] = {"name": self.experimentName, "runs": []}
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
        runDict: Dict[str, Any] = {"id": name, "node": []}
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
        nodeDict: Dict[str, Any] = {"id": name, "devices": []}

        for key, value in node.attrs.items():
            nodeDict[key] = str(value)

        for device_id, device in node.items():
            deviceDict: Dict[str, Any] = {
                "id": device_id,
            }
            if data:
                deviceDict["data"] = device[:]

            for key, value in device.attrs.items():
                deviceDict[key] = str(value)

            nodeDict["devices"].append(deviceDict)

        return nodeDict
