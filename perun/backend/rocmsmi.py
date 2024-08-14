"""ROCM Backend."""

import importlib
import logging
from typing import Callable, Dict, List, Set, Tuple

import numpy as np

from perun.backend.backend import Backend
from perun.data_model.measurement_type import Magnitude, MetricMetaData, Unit
from perun.data_model.sensor import DeviceType, Sensor

log = logging.getLogger("perun")


class ROCMBackend(Backend):
    """ROCMBackend.

    Initialises sensors to get data from AMD GPUs.
    """

    id = "rocm-smi"
    name = "AMD ROCM"
    description: str = "Access GPU information from rocm-smi python bindings."

    def setup(self):
        """Init rocm object."""
        self.rocml = importlib.import_module("pyrsmi").rocml
        self.rocml.smi_initialize()
        self._metadata = {
            "rocm_smi_version": self.rocml.smi_get_version(),
            "rocm_kernel_version": self.rocml.smi_get_kernel_version(),
            "source": "ROCM SMI",
        }

    def close(self):
        """Backend cleanup."""
        self.rocml.smi_shutdown()

    def availableSensors(self) -> Dict[str, Tuple]:
        """Return string ids of visible devices.

        Returns
        -------
        Set[str]
            Set with sensor ids.
        """
        devices = {}
        for i in range(self.rocml.smi_get_device_count()):
            device_id = self.rocml.smi_get_device_id(i)
            try:
                if np.float32(self.rocml.smi_get_device_average_power(device_id)) > 0:
                    devices[f"ROCM:{i}_POWER"] = (self.id, DeviceType.GPU, Unit.WATT)
            except self.rocml.RocmSMIError as e:
                log.info(e)
                log.info(f"Could not get power usage for device rocm:{i} {device_id}")

            try:
                if np.uint64(self.rocml.smi_get_device_memory_total(device_id)) > 0:
                    devices[f"ROCM:{i}_MEM"] = (self.id, DeviceType.GPU, Unit.BYTE)
            except self.rocml.RocmSMIError as e:
                log.info(e)
                log.info(f"Could not get memory usage for device rocm:{i} {device_id}")

        return devices

    def getSensors(self, deviceList: Set[str]) -> List[Sensor]:
        """Gather sensor object based on a set of device ids.

        Parameters
        ----------
        deviceList : Set[str]
            Set containing divice ids.

        Returns
        -------
        List[Sensor]
            List with Sensor objects.
        """
        self.rocml.smi_initialize()

        devices = []

        for deviceStr in deviceList:
            id, measurement_type = deviceStr.split("_")

            device_idx = id[5:]
            if measurement_type == "POWER":
                devices.append(self._getPowerSensor(int(device_idx)))
            elif measurement_type == "MEM":
                devices.append(self._getMemSensor(int(device_idx)))
        return devices

    def _getPowerSensor(self, device_idx: int) -> Sensor:
        device_id = self.rocml.smi_get_device_id(device_idx)
        log.debug(f"Setting up device {device_id}")

        name = f"{self.rocml.smi_get_device_name(device_id)}_{device_id}"
        device_type = DeviceType.GPU
        device_metadata = {
            "uuid": str(self.rocml.smi_get_device_unique_id(device_id)),
            "name": self.rocml.smi_get_device_name(device_id),
            **self._metadata,
        }

        data_type = MetricMetaData(
            Unit.WATT,
            Magnitude.ONE,
            np.dtype("float32"),
            np.float32(0),
            np.finfo("float32").max,
            np.float32(0),
        )
        return Sensor(
            name + "_POWER",
            device_type,
            device_metadata,
            data_type,
            self._getPowerCallback(device_id),
        )

    def _getPowerCallback(self, handle: int) -> Callable[[], np.number]:
        def func() -> np.number:
            try:
                return np.float32(self.rocml.smi_get_device_average_power(handle))
            except self.rocml.RocmSMIError as e:
                log.warning(f"Could not get power usage for device {handle}")
                log.exception(e)
                return np.float32(0)

        return func

    def _getMemSensor(self, device_idx: int) -> Sensor:
        device_id = self.rocml.smi_get_device_id(device_idx)
        log.debug(f"Setting up device {device_id}")

        name = f"{self.rocml.smi_get_device_name(device_id)}_{device_id}"
        device_type = DeviceType.GPU
        device_metadata = {
            "uuid": str(self.rocml.smi_get_device_unique_id(device_id)),
            "name": self.rocml.smi_get_device_name(device_id),
            **self._metadata,
        }

        max_memory = np.uint64(self.rocml.smi_get_device_memory_total(device_id))
        data_type = MetricMetaData(
            Unit.BYTE,
            Magnitude.ONE,
            np.dtype("uint64"),
            np.uint64(0),
            max_memory,
            np.uint64(0),
        )
        return Sensor(
            name + "_MEM",
            device_type,
            device_metadata,
            data_type,
            self._getMemCallback(device_id),
        )

    def _getMemCallback(self, handle) -> Callable[[], np.number]:
        def func() -> np.number:
            try:
                return np.float32(self.rocml.smi_get_device_memory_used(handle))
            except self.rocml.RocmSMIError as e:
                log.warning(f"Could not get memory usage for device {handle}")
                log.exception(e)
                return np.float32(0)

        return func
