"""Nvidia Mangement Library Source definition."""
from typing import Callable, Set

import numpy as np
import pynvml
from pynvml import NVMLError

from perun import log
from perun.units import Watt

from .backend import Backend, backend
from .device import Device


@backend
class NVMLSource(Backend):
    """NVMLSource class.

    Setups connection to NVML and creates relevant devices
    """

    name = "NVIDIA ML"
    description: str = "Access GPU information from NVML python bindings"

    def __init__(self) -> None:
        """Init NVIDIA ML Backend."""
        super().__init__()

    def close(self):
        """Backend shutdown code."""
        pynvml.nvmlShutdown()

    def visibleDevices(self) -> Set[str]:
        """
        Return string ids of visible devices.

        Returns:
            Set[str]: Set with device string ids
        """
        devices = set()
        for i in range(pynvml.nvmlDeviceGetCount()):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            devices.add(pynvml.nvmlDeviceGetUUID(handle).decode("utf-8"))
        return devices

    def getDevices(self, deviceList: Set[str]):
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

        for device in deviceList:
            try:
                handle = pynvml.nvmlDeviceGetHandleByUUID(device.encode())

                name = f"CUDA:{device}"
                long_name = f"{pynvml.nvmlDeviceGetName(handle).decode('utf-8')}"
                max_power = np.uint32(pynvml.nvmlDeviceGetPowerManagementLimit(handle))

                self.devices.append(
                    Device(
                        name,
                        long_name,
                        Watt(),
                        "mili",
                        0,
                        max_power,
                        "uint32",
                        getCallback(handle),
                    )
                )
            except NVMLError as e:
                log.debug(f"Could not find device {device}")
                log.debug(e)

        return self.devices

    def setup(self):
        """Init pynvml and gather number of devices."""
        pynvml.nvmlInit()
        deviceCount = pynvml.nvmlDeviceGetCount()
        log.debug(f"NVML Device count: {deviceCount}")


NVMLSource()
