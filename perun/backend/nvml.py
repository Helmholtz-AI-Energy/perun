"""Nvidia Mangement Library Source definition."""

import importlib
import logging
from typing import Callable, Dict, List, Set, Tuple

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
        self._metadata = {
            "cuda_version": str(self.pynvml.nvmlSystemGetCudaDriverVersion()),
            "driver_version": str(self.pynvml.nvmlSystemGetDriverVersion()),
            "source": "Nvidia Managment Library",
        }

        self.clock_types = {
            "CLOCK_SM": self.pynvml.NVML_CLOCK_SM,
            "CLOCK_MEM": self.pynvml.NVML_CLOCK_MEM,
            "CLOCK_GRAPHICS": self.pynvml.NVML_CLOCK_GRAPHICS,
        }

        log.info(f"NVML Device count: {deviceCount}")

    def close(self):
        """Backend shutdown code."""
        self.pynvml.nvmlShutdown()

    def availableSensors(self) -> Dict[str, Tuple]:
        """Return string ids of visible devices.

        Returns
        -------
        Set[str]
            Set with sensor ids.
        """
        devices = {}
        for i in range(self.pynvml.nvmlDeviceGetCount()):
            handle = self.pynvml.nvmlDeviceGetHandleByIndex(i)
            try:
                if np.uint32(self.pynvml.nvmlDeviceGetPowerUsage(handle)) > 0:
                    devices[f"CUDA:{i}_POWER"] = (self.id, DeviceType.GPU, Unit.WATT)
            except self.pynvml.NVMLError as e:
                log.info(e)
                log.info(f"Could not get power usage for device {handle}")

            try:
                if np.uint64(self.pynvml.nvmlDeviceGetMemoryInfo(handle).used) > 0:
                    devices[f"CUDA:{i}_MEM"] = (self.id, DeviceType.GPU, Unit.BYTE)
            except self.pynvml.NVMLError as e:
                log.info(e)
                log.info(f"Could not get memory usage for device {handle}")

            for clock_name, clock_id in self.clock_types.items():
                try:
                    if (
                        np.uint32(self.pynvml.nvmlDeviceGetClockInfo(handle, clock_id))
                        > 0
                    ):
                        devices[f"CUDA:{i}_{clock_name}"] = (
                            self.id,
                            DeviceType.GPU,
                            Unit.HZ,
                        )
                except self.pynvml.NVMLError as e:
                    log.info(e)
                    log.info(f"Could not get {clock_name} usage for device {handle}")

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

        devices = []

        for device_id in deviceList:
            device_idx = int(device_id.split(":")[1][0])
            measurement_unit = device_id.split("_", 1)[1]

            if measurement_unit == "POWER":
                devices.append(self._getPowerSensor(device_idx))
            elif measurement_unit == "MEM":
                devices.append(self._getMemorySensor(device_idx))
            elif measurement_unit.startswith("CLOCK"):
                devices.append(self._getClockSensor(device_idx, measurement_unit))

        return devices

    def _getPowerSensor(self, device_idx: int) -> Sensor:
        handle = self.pynvml.nvmlDeviceGetHandleByIndex(device_idx)
        uuid = self.pynvml.nvmlDeviceGetUUID(handle)
        log.debug(f"Index: {device_idx} - UUID : {uuid}")

        name = f"CUDA:{device_idx}"
        device_type = DeviceType.GPU
        device_metadata = {
            "uuid": uuid,
            "name": str(self.pynvml.nvmlDeviceGetName(handle)),
            **self._metadata,
        }
        try:
            max_power: np.number = np.uint32(
                self.pynvml.nvmlDeviceGetPowerManagementDefaultLimit(handle)
            )
            log.debug(f"Device {uuid} Max Power : {max_power}")
        except self.pynvml.NVMLError as e:
            log.info(f"Could not get max power for device {uuid}")
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
        return Sensor(
            name + "_POWER",
            device_type,
            device_metadata,
            data_type,
            self._getPowerCallback(handle),
        )

    def _getPowerCallback(self, handle) -> Callable[[], np.number]:
        def func() -> np.number:
            try:
                return np.uint32(self.pynvml.nvmlDeviceGetPowerUsage(handle))
            except self.pynvml.NVMLError as e:
                log.warning(
                    f"Could not get power usage for device {self.pynvml.nvmlDeviceGetUUID(handle)}"
                )
                log.exception(e)
                return np.uint32(0)

        return func

    def _getMemorySensor(self, device_idx: int) -> Sensor:
        handle = self.pynvml.nvmlDeviceGetHandleByIndex(device_idx)
        uuid = self.pynvml.nvmlDeviceGetUUID(handle)
        log.debug(f"Index: {device_idx} - UUID : {uuid}")

        name = f"CUDA:{device_idx}"
        device_type = DeviceType.GPU
        device_metadata = {
            "uuid": uuid,
            "name": str(self.pynvml.nvmlDeviceGetName(handle)),
            **self._metadata,
        }

        try:
            max_memory: np.number = np.uint64(
                self.pynvml.nvmlDeviceGetMemoryInfo(handle).total
            )
            log.debug(f"Device {device_idx} Max Memory : {max_memory}")
        except self.pynvml.NVMLError as e:
            log.info(f"Could not get max memory for device {device_idx}")
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
        return Sensor(
            name + "_MEM",
            device_type,
            device_metadata,
            data_type,
            self._getUsedMemCallback(handle),
        )

    def _getUsedMemCallback(self, handle) -> Callable[[], np.number]:
        def func() -> np.number:
            try:
                return np.uint64(self.pynvml.nvmlDeviceGetMemoryInfo(handle).used)
            except self.pynvml.NVMLError as e:
                log.warning(
                    f"Could not get memory usage for device {self.pynvml.nvmlDeviceGetUUID(handle)}"
                )
                log.exception(e)
                return np.uint32(0)

        return func

    def _getClockSensor(self, device_idx: int, clock_type: str) -> Sensor:
        handle = self.pynvml.nvmlDeviceGetHandleByIndex(device_idx)
        uuid = self.pynvml.nvmlDeviceGetUUID(handle)
        log.debug(f"Index: {device_idx} - UUID : {uuid}")

        name = f"CUDA:{device_idx}"
        device_type = DeviceType.GPU
        device_metadata = {
            "uuid": uuid,
            "name": str(self.pynvml.nvmlDeviceGetName(handle)),
            **self._metadata,
        }

        try:
            max_clock = np.uint32(
                self.pynvml.nvmlDeviceGetMaxClockInfo(
                    handle, self.clock_types[clock_type]
                )
            )
            log.debug(f"Device {device_idx} Max Clock {clock_type} : {max_clock}")
        except self.pynvml.NVMLError as e:
            log.info(f"Could not get max clock {clock_type} for device {device_idx}")
            log.info(e)
            max_clock = np.uint32(np.iinfo("uint32").max)

        try:
            current_clock = np.uint32(
                self.pynvml.nvmlDeviceGetClockInfo(handle, self.clock_types[clock_type])
            )
            log.debug(
                f"Device {device_idx} Current Clock {clock_type} : {current_clock}"
            )
        except self.pynvml.NVMLError as e:
            log.info(
                f"Could not get current clock {clock_type} for device {device_idx}"
            )
            log.info(e)
            current_clock = np.uint32(0)

        data_type = MetricMetaData(
            Unit.HZ,
            Magnitude.MEGA,
            np.dtype("uint32"),
            np.uint32(0),
            max_clock,
            np.uint32(0),
        )
        return Sensor(
            name + f"_{clock_type}",
            device_type,
            device_metadata,
            data_type,
            self._getClockCallback(handle, self.clock_types[clock_type]),
        )

    def _getClockCallback(self, handle, clock_type) -> Callable[[], np.number]:
        def func() -> np.number:
            try:
                return np.uint32(self.pynvml.nvmlDeviceGetClockInfo(handle, clock_type))
            except self.pynvml.NVMLError as e:
                log.warning(
                    f"Could not get clock for device {self.pynvml.nvmlDeviceGetUUID(handle)}"
                )
                log.exception(e)
                return np.uint32(0)

        return func
