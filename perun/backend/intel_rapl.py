"""Defines Intel RAPL related classes."""
import os
import re
from io import IOBase
from pathlib import Path
from typing import Callable, List, Set

import cpuinfo
import numpy as np

from perun import log
from perun.data_model.measurement_type import Magnitude, MetricMetaData, Unit

from ..data_model.sensor import DeviceType, Sensor
from .backend import Backend, backend

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
        log.info("Initialized Intel RAPL")

    def setup(self):
        """Check Intel RAPL access."""
        cpuInfo = cpuinfo.get_cpu_info()
        self.metadata = {
            "vendor_id": cpuInfo["vendor_id_raw"],
            "brand": cpuInfo["brand_raw"],
            "arch": cpuInfo["arch_string_raw"],
            "hz_advertised": cpuInfo["hz_advertised_friendly"],
            "hz_actual": cpuInfo["hz_actual_friendly"],
            "l1_data_cache_size": cpuInfo["l1_data_cache_size"],
            "l1_instruction_cache_size": cpuInfo["l1_instruction_cache_size"],
            "l2_cache_size": cpuInfo["l2_cache_size"],
            "l2_cache_line_size": cpuInfo["l2_cache_line_size"],
            "l2_cache_associativity": cpuInfo["l2_cache_associativity"],
            "l3_cache_size": cpuInfo["l3_cache_size"],
            "source": "Intel RAPL",
        }
        log.debug(f"CPU info metadata: {self.metadata}")

        raplPath = Path(RAPL_PATH)

        def getCallback(file: IOBase) -> Callable[[], np.number]:
            def func() -> np.number:
                file.seek(0)
                return np.uint64(file.readline().strip())

            return func

        if not raplPath.exists():
            raise ImportWarning("No powercap interface")

        self._files = []
        packageDevices = []
        foundPsys = False
        for child in raplPath.iterdir():
            log.debug(child)
            match = re.match(DIR_RGX, child.name)
            if match:
                if os.access(child / "energy_uj", os.R_OK):
                    socket = match.groups()[0]
                    with open(child / "name", "r") as file:
                        device_name = file.readline().strip()

                    log.debug(device_name)

                    if "dram" in device_name:
                        devType = DeviceType.RAM
                    elif "package" in device_name:
                        devType = DeviceType.CPU
                    elif "psys" in device_name:
                        devType = DeviceType.CPU
                        foundPsys = True
                    else:
                        devType = DeviceType.OTHER

                    if devType != DeviceType.OTHER:
                        with open(child / "max_energy_range_uj", "r") as file:
                            max_energy = np.uint64(file.readline().strip())
                        dataType = MetricMetaData(
                            Unit.JOULE,
                            Magnitude.MICRO,
                            np.dtype("uint64"),
                            np.uint64(0),
                            max_energy,
                            max_energy,
                        )

                        energy_path = str(child / "energy_uj")
                        energy_file = open(energy_path, "r")
                        self._files.append(energy_file)
                        device = Sensor(
                            f"{devType.value}_{socket}_{device_name}",
                            devType,
                            self.metadata,
                            dataType,
                            getCallback(energy_file),
                        )

                        self.devices[device.id] = device
                        if "package" in device_name:
                            packageDevices.append(device)

                        for grandchild in child.iterdir():
                            match = re.match(SUBDIR_RGX, grandchild.name)
                            if match:
                                with open(grandchild / "name", "r") as file:
                                    device_name = file.readline().strip()
                                if "dram" in device_name:
                                    devType = DeviceType.RAM
                                elif "package" in device_name:
                                    devType = DeviceType.CPU
                                elif "psys" in device_name:
                                    devType = DeviceType.CPU
                                    foundPsys = True
                                else:
                                    devType = DeviceType.OTHER

                                if devType != DeviceType.OTHER:
                                    with open(
                                        child / "max_energy_range_uj", "r"
                                    ) as file:
                                        max_energy = np.uint64(file.readline().strip())

                                    dataType = MetricMetaData(
                                        Unit.JOULE,
                                        Magnitude.MICRO,
                                        np.dtype("uint64"),
                                        np.uint64(0),
                                        max_energy,
                                        max_energy,
                                    )

                                    energy_path = str(grandchild / "energy_uj")
                                    energy_file = open(energy_path, "r")
                                    self._files.append(energy_file)
                                    device = Sensor(
                                        f"{devType.value}_{socket}_{device_name}",
                                        devType,
                                        self.metadata,
                                        dataType,
                                        getCallback(energy_file),
                                    )
                                    log.debug(device)
                                    self.devices[device.id] = device

                                    if "package" in device_name:
                                        packageDevices.append(device)

        if foundPsys:
            for pkg in packageDevices:
                del self.devices[pkg.id]

        log.debug("IntelRapl devices", self.devices)

    def close(self) -> None:
        """Backend shutdown code (does nothing for intel rapl)."""
        log.debug("Closing files")
        for file in self._files:
            file.close()
        return

    def visibleSensors(self) -> Set[str]:
        """
        Return string ids of visible devices.

        Returns:
            Set[str]: Set with device string ids
        """
        log.debug(self.devices)
        return {id for id, device in self.devices.items()}

    def getSensors(self, deviceList: Set[str]) -> List[Sensor]:
        """
        Gather devive objects based on a set of device ids.

        Args:
            deviceList (Set[str]): Set containing devices ids

        Returns:
            List[Device]: Device objects
        """
        return [self.devices[deviceId] for deviceId in deviceList]


IntelRAPLBackend()
