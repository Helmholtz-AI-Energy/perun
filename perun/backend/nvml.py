"""Nvidia Mangement Library Source definition."""
from typing import Callable, Set

import numpy as np
import pynvml
from pynvml import NVMLError

from perun import log
from perun.data_model.measurement_type import Magnitude, MetricMetaData, Unit

from ..data_model.sensor import DeviceType, Sensor
from .backend import Backend, backend


@backend
class NVMLBackend(Backend):
    """NVMLSource class.

    Setups connection to NVML and creates relevant devices
    """

    name = "NVIDIA ML"
    description: str = "Access GPU information from NVML python bindings"

    def __init__(self) -> None:
        """Init NVIDIA ML Backend."""
        super().__init__()
        log.info("Initialized NVML Backend")

    def setup(self):
        """Init pynvml and gather number of devices."""
        pynvml.nvmlInit()
        deviceCount = pynvml.nvmlDeviceGetCount()
        self.metadata = {
            "cuda_version": pynvml.nvmlSystemGetCudaDriverVersion(),
            "driver_version": pynvml.nvmlSystemGetDriverVersion(),
            "source": "Nvidia Managment Library",
        }

        log.debug(f"NVML Device count: {deviceCount}")

    def close(self):
        """Backend shutdown code."""
        pynvml.nvmlShutdown()

    def visibleSensors(self) -> Set[str]:
        """
        Return string ids of visible devices.

        Returns:
            Set[str]: Set with device string ids
        """
        devices = set()
        for i in range(pynvml.nvmlDeviceGetCount()):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            devices.add(pynvml.nvmlDeviceGetUUID(handle))
        return devices

    def getSensors(self, deviceList: Set[str]):
        """
        Gather device objects based on a set of device ids.

        Args:
            deviceList (Set[str]): Set containing devices ids

        Returns:
            List[Device]: Device objects
        """

        def getCallback(handle) -> Callable[[], np.number]:
            def func() -> np.number:
                return np.uint32(pynvml.nvmlDeviceGetPowerUsage(handle))

            return func

        devices = []
        for deviceId in deviceList:
            try:
                handle = pynvml.nvmlDeviceGetHandleByUUID(deviceId.encode())
                index = pynvml.nvmlDeviceGetIndex(handle)

                name = f"CUDA:{index}"
                device_type = DeviceType.GPU
                device_metadata = {
                    "uuid": deviceId,
                    "name": pynvml.nvmlDeviceGetName(handle),
                    **self.metadata,
                }
                max_power = np.uint32(pynvml.nvmlDeviceGetPowerManagementLimit(handle))

                data_type = MetricMetaData(
                    Unit.WATT,
                    Magnitude.MILI,
                    np.dtype("uint32"),
                    np.uint32(0),
                    np.uint32(max_power),
                    np.uint32(0),
                )
                devices.append(
                    Sensor(
                        name,
                        device_type,
                        device_metadata,
                        data_type,
                        getCallback(handle),
                    )
                )
            except NVMLError as e:
                log.debug(f"Could not find device {deviceId}")
                log.debug(e)

        return devices


NVMLBackend()
