"""ROCM Backend."""

import importlib
import logging
from typing import Callable, List, Set

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
        self.metadata = {
            "rocm_smi_version": self.rocml.smi_get_version(),
            "rocm_kernel_version": self.rocml.smi_get_kernel_version(),
            "source": "ROCM SMI",
        }

    def close(self):
        """Backend cleanup."""
        self.rocml.smi_shutdown()

    def visibleSensors(self) -> Set[str]:
        """Return string ids of visible devices.

        Returns
        -------
        Set[str]
            Set with sensor ids.
        """
        devices = set()
        for i in range(self.rocml.smi_get_device_count()):
            devices.add(str(i))
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

        def getPowerCallback(handle) -> Callable[[], np.number]:
            def func() -> np.number:
                return np.float32(self.rocml.smi_get_device_average_power(handle))

            return func

        def getMemCallback(handle) -> Callable[[], np.number]:
            def func() -> np.number:
                return np.float32(self.rocml.smi_get_device_memory_used(handle))

            return func

        devices = []

        for deviceStr in deviceList:
            deviceId = int(deviceStr)
            log.debug(f"Setting up device {deviceId}")

            name = f"{self.rocml.smi_get_device_name(deviceId)}_{deviceId}"
            device_type = DeviceType.GPU
            device_metadata = {
                "uuid": deviceId,
                "name": self.rocml.smi_get_device_name(deviceId),
                **self.metadata,
            }

            data_type = MetricMetaData(
                Unit.WATT,
                Magnitude.ONE,
                np.dtype("float32"),
                np.float32(0),
                np.finfo("float32").max,
                np.float32(0),
            )
            devices.append(
                Sensor(
                    name + "_POWER",
                    device_type,
                    device_metadata,
                    data_type,
                    getPowerCallback(deviceId),
                )
            )
            max_memory = np.uint64(self.rocml.smi_get_device_memory_total(deviceId))
            data_type = MetricMetaData(
                Unit.BYTE,
                Magnitude.ONE,
                np.dtype("uint64"),
                np.uint64(0),
                max_memory,
                np.uint64(0),
            )
            devices.append(
                Sensor(
                    name + "_MEM",
                    device_type,
                    device_metadata,
                    data_type,
                    getMemCallback(deviceId),
                )
            )
        return devices
