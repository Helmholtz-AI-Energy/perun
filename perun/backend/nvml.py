"""Nvidia Mangement Library Source definition."""

import importlib
import logging
from typing import Callable, List, Set

import numpy as np

from perun.backend.backend import Backend
from perun.data_model.measurement_type import Magnitude, MetricMetaData, Unit
from perun.data_model.sensor import DeviceType, Sensor

log = logging.getLogger("perun")


class NVMLBackend(Backend):
    """NVMLSource class.

    Setups connection to NVML and creates relevant devices
    """

    id = "nvlm"
    name = "NVIDIA ML"
    description: str = "Access GPU information from NVML python bindings"

    def setup(self):
        """Init pynvml and gather number of devices."""
        self.pynvml = importlib.import_module("pynvml")
        self.pynvml.nvmlInit()
        deviceCount = self.pynvml.nvmlDeviceGetCount()
        self.metadata = {
            "cuda_version": str(self.pynvml.nvmlSystemGetCudaDriverVersion()),
            "driver_version": str(self.pynvml.nvmlSystemGetDriverVersion()),
            "source": "Nvidia Managment Library",
        }

        log.info(f"NVML Device count: {deviceCount}")

    def close(self):
        """Backend shutdown code."""
        self.pynvml.nvmlShutdown()

    def visibleSensors(self) -> Set[str]:
        """Return string ids of visible devices.

        Returns
        -------
        Set[str]
            Set with sensor ids.
        """
        devices = set()
        for i in range(self.pynvml.nvmlDeviceGetCount()):
            handle = self.pynvml.nvmlDeviceGetHandleByIndex(i)
            devices.add(self.pynvml.nvmlDeviceGetUUID(handle))
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
        self.pynvml.nvmlInit()

        def getCallback(handle) -> Callable[[], np.number]:
            def func() -> np.number:
                try:
                    return np.uint32(self.pynvml.nvmlDeviceGetPowerUsage(handle))
                except self.pynvml.NVMLError as e:
                    log.warning(f"Could not get power usage for device {deviceId}")
                    log.exception(e)
                    return np.uint32(0)

            return func

        def getUsedMemCallback(handle) -> Callable[[], np.number]:
            def func() -> np.number:
                try:
                    return np.uint64(self.pynvml.nvmlDeviceGetMemoryInfo(handle).used)
                except self.pynvml.NVMLError as e:
                    log.warning(f"Could not get memory usage for device {deviceId}")
                    log.exception(e)
                    return np.uint32(0)

            return func

        def getClockCallback(handle, clock_type) -> Callable[[], np.number]:
            def func() -> np.number:
                try:
                    return np.uint32(
                        self.pynvml.nvmlDeviceGetClockInfo(handle, clock_type)
                    )
                except self.pynvml.NVMLError as e:
                    log.warning(f"Could not get clock for device {deviceId}")
                    log.exception(e)
                    return np.uint32(0)

            return func

        devices = []

        for deviceId in deviceList:
            try:
                log.debug(f"Getting handle from '{deviceId}'")
                handle = self.pynvml.nvmlDeviceGetHandleByUUID(deviceId)
                index = self.pynvml.nvmlDeviceGetIndex(handle)
                log.debug(f"Index: {index} - Handle : {handle}")

                name = f"CUDA:{index}"
                device_type = DeviceType.GPU
                device_metadata = {
                    "uuid": deviceId,
                    "name": str(self.pynvml.nvmlDeviceGetName(handle)),
                    **self.metadata,
                }
                try:
                    max_power: np.number = np.uint32(
                        self.pynvml.nvmlDeviceGetPowerManagementDefaultLimit(handle)
                    )
                    log.debug(f"Device {deviceId} Max Power : {max_power}")
                except self.pynvml.NVMLError as e:
                    log.info(f"Could not get max power for device {deviceId}")
                    log.info(e)
                    max_power = np.uint32(np.iinfo("uint32").max)

                data_type = MetricMetaData(
                    Unit.WATT,
                    Magnitude.MILI,
                    np.dtype("uint32"),
                    np.uint32(0),
                    max_power,
                    np.uint32(0),
                )
                devices.append(
                    Sensor(
                        name + "_POWER",
                        device_type,
                        device_metadata,
                        data_type,
                        getCallback(handle),
                    )
                )
                try:
                    max_memory: np.number = np.uint64(
                        self.pynvml.nvmlDeviceGetMemoryInfo(handle).total
                    )
                    log.debug(f"Device {deviceId} Max Memory : {max_memory}")
                except self.pynvml.NVMLError as e:
                    log.info(f"Could not get max memory for device {deviceId}")
                    log.info(e)
                    max_memory = np.uint64(np.iinfo("uint64").max)

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
                        getUsedMemCallback(handle),
                    )
                )

                for clock_name, id in {
                    "SM": self.pynvml.NVML_CLOCK_SM,
                    "MEM": self.pynvml.NVML_CLOCK_MEM,
                    "GRAPHICS": self.pynvml.NVML_CLOCK_GRAPHICS,
                }.items():
                    try:
                        max_clock = np.uint32(
                            self.pynvml.nvmlDeviceGetMaxClockInfo(handle, id)
                        )
                        log.debug(
                            f"Device {deviceId} Max Clock {clock_name} : {max_clock}"
                        )
                    except self.pynvml.NVMLError as e:
                        log.info(
                            f"Could not get max clock {clock_name} for device {deviceId}"
                        )
                        log.info(e)
                        max_clock = np.uint32(np.iinfo("uint32").max)

                    try:
                        current_clock = np.uint32(
                            self.pynvml.nvmlDeviceGetClockInfo(handle, id)
                        )
                        log.debug(
                            f"Device {deviceId} Current Clock {clock_name} : {current_clock}"
                        )
                    except self.pynvml.NVMLError as e:
                        log.info(
                            f"Could not get current clock {clock_name} for device {deviceId}"
                        )
                        log.info(e)
                        current_clock = np.uint32(0)
                        continue

                    data_type = MetricMetaData(
                        Unit.HZ,
                        Magnitude.MEGA,
                        np.dtype("uint32"),
                        np.uint32(0),
                        max_clock,
                        np.uint32(0),
                    )
                    devices.append(
                        Sensor(
                            name + "_CLOCK" + clock_name,
                            device_type,
                            device_metadata,
                            data_type,
                            getClockCallback(handle, id),
                        )
                    )

            except self.pynvml.NVMLError as e:
                log.warning(f"Could not find device {deviceId}")
                log.warning(e)

        return devices
