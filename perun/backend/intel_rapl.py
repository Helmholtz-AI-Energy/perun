"""Defines Intel RAPL related classes."""
import os
import re
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
            "hardware": cpuInfo["hardware_raw"],
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

        raplPath = Path(RAPL_PATH)

        def getCallback(filePath) -> Callable[[], np.number]:
            def func() -> np.number:
                return np.uint64(open(filePath, "r").readline().strip())

            return func

        if not raplPath.exists():
            raise ImportWarning("No powercap interface")

        for child in raplPath.iterdir():
            match = re.match(DIR_RGX, child.name)
            if match:
                if os.access(child / "energy_uj", os.R_OK):
                    socket = match.groups()[0]
                    device_name = open(child / "name", "r").readline().strip()

                    if "dram" in device_name:
                        devType = DeviceType.RAM
                    elif "package" in device_name:
                        devType = DeviceType.CPU
                    else:
                        devType = DeviceType.OTHER

                    max_energy = np.uint64(
                        open(child / "max_energy_range_uj", "r").readline().strip()
                    )
                    dataType = MetricMetaData(
                        Unit.JOULE,
                        Magnitude.MICRO,
                        np.dtype("uint64"),
                        np.uint64(0),
                        max_energy,
                        max_energy,
                    )

                    energy_path = str(child / "energy_uj")
                    device = Sensor(
                        f"{type}_{socket}_{device_name}",
                        devType,
                        self.metadata,
                        dataType,
                        getCallback(energy_path),
                    )

                    self.devices[device.id] = device

                    for grandchild in child.iterdir():
                        match = re.match(SUBDIR_RGX, grandchild.name)
                        if match:
                            device_name = (
                                open(grandchild / "name", "r").readline().strip()
                            )
                            if "dram" in device_name:
                                devType = DeviceType.RAM
                            elif "package" in device_name:
                                devType = DeviceType.CPU
                            else:
                                devType = DeviceType.OTHER

                            max_energy = np.uint64(
                                open(child / "max_energy_range_uj", "r")
                                .readline()
                                .strip()
                            )
                            dataType = MetricMetaData(
                                Unit.JOULE,
                                Magnitude.MICRO,
                                np.dtype("uint64"),
                                np.uint64(0),
                                max_energy,
                                max_energy,
                            )

                            energy_path = str(grandchild / "energy_uj")
                            device = Sensor(
                                f"{type}_{socket}_{device_name}",
                                devType,
                                self.metadata,
                                dataType,
                                getCallback(energy_path),
                            )
                            self.devices[device.id] = device

    def close(self) -> None:
        """Backend shutdown code (does nothing for intel rapl)."""
        return

    def visibleSensors(self) -> Set[str]:
        """
        Return string ids of visible devices.

        Returns:
            Set[str]: Set with device string ids
        """
        return {device.id for device in self.devices}

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
