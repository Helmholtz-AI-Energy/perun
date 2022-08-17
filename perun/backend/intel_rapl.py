"""Defines Intel RAPL related classes."""
from typing import Callable, Set, List

from .backend import Backend, backend
from .device import Device
from perun.units import Joule
from perun import log

import cpuinfo


@backend
class IntelRAPLBackend(Backend):
    """Intel RAPL as a source of cpu and memory devices.

    Uses pyRAPL to gather device information and creates metrics for each available device
    """

    name = "Intel RAPL"
    description = "Reads energy usage from CPUs and DRAM using Intel RAPL"

    def __init__(self) -> None:
        """Init IntelRAPLBackend."""
        super().__init__()
        log.debug("Initialized pyrapl")

    def setup(self):
        """Import pyrapl and gather basic information."""
        import pyRAPL

        self.sensor = pyRAPL.Sensor()
        cpuInfo = cpuinfo.get_cpu_info()
        self.cpu_name = cpuInfo["brand_raw"]
        self.thread_count = cpuInfo["count"]

    def close(self) -> None:
        """Backend shutdown code (does nothing for intel rapl)."""
        return

    def visibleDevices(self) -> Set[str]:
        """
        Return string ids of visible devices.

        Returns:
            Set[str]: Set with device string ids
        """
        visibleDevices = set()
        for device in self.sensor._available_devices:
            for socket in self.sensor._socket_ids:
                visibleDevices.add(f"{device.name}_{socket}")
        return visibleDevices

    def getDevices(self, deviceList: Set[str]) -> List[Device]:
        """
        Gather devive objects based on a set of device ids.

        Args:
            deviceList (Set[str]): Set containing devices ids

        Returns:
            List[Device]: Device objects
        """

        def getCallback(device_api, socket) -> Callable[[], float]:
            def func() -> float:
                return device_api.energy()[socket]

            return func

        for device, device_api in self.sensor._device_api.items():
            for socket in self.sensor._socket_ids:

                if f"{device.name}_{socket}" in deviceList:

                    deviceName = "CPU" if device.name == "PKG" else "DRAM"
                    name = f"{socket}_{deviceName}"
                    long_name = f"{self.cpu_name}:{socket}_{deviceName}"

                    self.devices.append(
                        Device(
                            name,
                            long_name,
                            Joule(),
                            "micro",
                            getCallback(device_api, socket),
                        )
                    )

        return self.devices


IntelRAPLBackend()
