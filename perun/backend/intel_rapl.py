"""Defines Intel RAPL related classes."""
import os
import re
from pathlib import Path
from typing import Callable, List, Set

import cpuinfo
import numpy as np

from perun import log
from perun.units import Joule

from .backend import Backend, backend
from .device import Device

RAPL_PATH = "/sys/class/powercap/"

DIR_RGX = r"intel-rapl:(\d)$"
SUBDIR_RGX = r"intel-rapl:\d:\d$"


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
        self.setup()

    def setup(self):
        """Check Intel RAPL access."""
        cpuInfo = cpuinfo.get_cpu_info()
        self.cpu_name = cpuInfo["brand_raw"]
        self.thread_count = cpuInfo["count"]

        raplPath = Path(RAPL_PATH)
        self._devices = {}

        if not raplPath.exists():
            raise ImportWarning("No powercap interface")

        for child in raplPath.iterdir():
            match = re.match(DIR_RGX, child.name)
            if match:
                if os.access(child / "energy_uj", os.R_OK):
                    socket = match.groups()[0]
                    device_name = open(child / "name", "r").readline().strip()
                    self._devices[f"{socket}_{device_name}"] = {
                        "max_energy_uj": np.uint64(
                            open(child / "max_energy_range_uj", "r").readline().strip()
                        ),
                        "energy_path": str(child / "energy_uj"),
                    }
                    for grandchild in child.iterdir():
                        match = re.match(SUBDIR_RGX, grandchild.name)
                        if match:
                            device_name = (
                                open(grandchild / "name", "r").readline().strip()
                            )
                            self._devices[f"{socket}_{device_name}"] = {
                                "max_energy_uj": np.uint64(
                                    open(grandchild / "max_energy_range_uj", "r")
                                    .readline()
                                    .strip()
                                ),
                                "energy_path": str(grandchild / "energy_uj"),
                            }

    def close(self) -> None:
        """Backend shutdown code (does nothing for intel rapl)."""
        return

    def visibleDevices(self) -> Set[str]:
        """
        Return string ids of visible devices.

        Returns:
            Set[str]: Set with device string ids
        """
        return set(self._devices.keys())

    def getDevices(self, deviceList: Set[str]) -> List[Device]:
        """
        Gather devive objects based on a set of device ids.

        Args:
            deviceList (Set[str]): Set containing devices ids

        Returns:
            List[Device]: Device objects
        """

        def getCallback(filePath) -> Callable[[], np.number]:
            def func() -> np.number:
                return np.uint64(open(filePath, "r").readline().strip())

            return func

        self.devices: List[Device] = []
        for device in deviceList:
            if device in self._devices:

                deviceInfo = self._devices[device]
                self.devices.append(
                    Device(
                        device,
                        f"{self.cpu_name}:{device}",
                        Joule(),
                        "micro",
                        0,
                        deviceInfo["max_energy_uj"],
                        "uint64",
                        getCallback(deviceInfo["energy_path"]),
                    )
                )

        return self.devices


IntelRAPLBackend()
