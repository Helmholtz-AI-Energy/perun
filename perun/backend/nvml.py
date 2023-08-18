"""Nvidia Mangement Library Source definition."""
from typing import Callable, List, Set

import numpy as np
import pynvml
from pynvml import NVMLError

from perun import log
from perun.backend.backend import Backend
from perun.data_model.measurement_type import Magnitude, MetricMetaData, Unit
from perun.data_model.sensor import DeviceType, Sensor
from perun.util import singleton


@singleton
class NVMLBackend(Backend):
    """NVMLSource class.

    Setups connection to NVML and creates relevant devices
    """

    id = "nvlm"
    name = "NVIDIA ML"
    description: str = "Access GPU information from NVML python bindings"

    def setup(self):
        """Init pynvml and gather number of devices."""
        pynvml.nvmlInit()
        deviceCount = pynvml.nvmlDeviceGetCount()
        self.metadata = {
            "cuda_version": str(pynvml.nvmlSystemGetCudaDriverVersion()),
            "driver_version": str(pynvml.nvmlSystemGetDriverVersion()),
            "source": "Nvidia Managment Library",
        }

        log.info(f"NVML Device count: {deviceCount}")

    def close(self):
        """Backend shutdown code."""
        pynvml.nvmlShutdown()

    def visibleSensors(self) -> Set[str]:
        """Return string ids of visible devices.

        :return: Set with string ids.
        :rtype: Set[str]
        """
        devices = set()
        for i in range(pynvml.nvmlDeviceGetCount()):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            devices.add(pynvml.nvmlDeviceGetUUID(handle))
        return devices

    def getSensors(self, deviceList: Set[str]) -> List[Sensor]:
        """Gather sensor objects based on a set of device ids.

        :param deviceList: Set containing device ids.
        :type deviceList: Set[str]
        :return: List with sensor objects
        :rtype: List[Sensor]
        """
        pynvml.nvmlInit()

        def getCallback(handle) -> Callable[[], np.number]:
            def func() -> np.number:
                return np.uint32(pynvml.nvmlDeviceGetPowerUsage(handle))

            return func

        def getUsedMemCallback(handle) -> Callable[[], np.number]:
            def func() -> np.number:
                return np.uint64(pynvml.nvmlDeviceGetMemoryInfo(handle).used)

            return func

        devices = []

        for deviceId in deviceList:
            try:
                log.debug(f"Getting handle from '{deviceId}'")
                handle = pynvml.nvmlDeviceGetHandleByUUID(deviceId)
                index = pynvml.nvmlDeviceGetIndex(handle)
                log.debug(f"Index: {index} - Handle : {handle}")

                name = f"CUDA:{index}"
                device_type = DeviceType.GPU
                device_metadata = {
                    "uuid": deviceId,
                    "name": str(pynvml.nvmlDeviceGetName(handle)),
                    **self.metadata,
                }
                max_power = np.uint32(
                    pynvml.nvmlDeviceGetPowerManagementDefaultLimit(handle)
                )
                log.debug(f"Device {deviceId} Max Power : {max_power}")

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
                max_memory = np.uint64(pynvml.nvmlDeviceGetMemoryInfo(handle).total)
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

            except NVMLError as e:
                log.warning(f"Could not find device {deviceId}")
                log.warning(e)

        return devices
