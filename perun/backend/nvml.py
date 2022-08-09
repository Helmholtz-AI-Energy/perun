"""Nvidia Mangement Library Source definition."""
from typing import Callable

from .backend import Backend, backend
from .device import Device
from perun.units import Watt
import logging
import pynvml
from pynvml import NVMLError


log = logging.getLogger(__name__)


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
        pynvml.nvmlInit()

    def close(self):
        """Backend shutdown code."""
        pynvml.nvmlShutdown()

    def visibleDevices(self) -> set[str]:
        """
        Return string ids of visible devices.

        Returns:
            set[str]: Set with device string ids
        """
        devices = set()
        for i in range(pynvml.nvmlDeviceGetCount()):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            devices.add(pynvml.nvmlDeviceGetUUID(handle).decode("utf-8"))
        return devices

    def getDevices(self, deviceList: set[str]):
        """
        Gather device objects based on a set of device ids.

        Args:
            deviceList (set[str]): Set containing devices ids

        Returns:
            list[Device]: Device objects
        """

        def getCallback(handle) -> Callable[[], float]:
            def func() -> float:
                return pynvml.nvmlDeviceGetPowerUsage(handle)

            return func

        for device in deviceList:
            try:
                handle = pynvml.nvmlDeviceGetHandleByUUID(device.encode())

                name = f"CUDA:{device}"
                long_name = f"{pynvml.nvmlDeviceGetName(handle).decode('utf-8')}"

                self.devices.append(
                    Device(name, long_name, Watt(), "mili", getCallback(handle))
                )
            except NVMLError as e:
                log.debug(f"Could not found device {device}")
                log.debug(e)

        return self.devices

    def _setup(self):

        deviceCount = pynvml.nvmlDeviceGetCount()

        log.debug(f"NVML Device count: {deviceCount}")


NVMLSource()
