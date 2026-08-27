"""Defines Intel RAPL related classes."""

import logging
import pprint as pp
import re
from io import IOBase
from pathlib import Path
from typing import Callable

import cpuinfo
import numpy as np

from perun.backend.backend import Backend
from perun.data_model.measurement_type import Magnitude, MetricMetaData, Number, Unit
from perun.data_model.sensor import DeviceType, Sensor

log = logging.getLogger(__name__)

RAPL_PATH = "/sys/class/powercap/"

DIR_RGX = r"intel-rapl:(\d)$"
SUBDIR_RGX = r"intel-rapl:\d:\d$"


class PowercapRAPLBackend(Backend):
    """Powercap RAPL as a source of cpu and memory devices.

    Uses the powercap filesystem files to gather device information and creates metrics for each available device
    """

    id = "powercap_rapl"
    name = "Powercap RAPL"
    description = "Reads energy usage from CPUs and DRAM using Powercap RAPL"

    def setup(self) -> None:
        """Check Intel RAPL access."""
        self._files: list[IOBase] = []

        cpuInfo = cpuinfo.get_cpu_info()
        self._metadata = {}
        for key, value in cpuInfo.items():
            if value is not None and value != "":
                self._metadata[key] = str(value)

        self.devices: dict[str, Sensor] = {}
        log.debug(f"CPU info metadata: {pp.pformat(self._metadata)}")

        raplPath = Path(RAPL_PATH)

        def getCallback(file: IOBase, file_path: str) -> Callable[[], Number]:
            def func() -> Number:
                try:
                    file.seek(0)
                    return np.uint64(file.readline().strip())
                except Exception as e:
                    log.warning(f"Error reading file: {file_path}")
                    log.exception(e)
                    return np.uint64(0)

            return func

        if not raplPath.exists():
            raise ImportWarning("No powercap interface")

        packageDevices = []
        packageFiles = []
        foundPsys = False
        for child in raplPath.iterdir():
            log.debug(child)
            match = re.match(DIR_RGX, child.name)
            log.debug(match)
            if match:
                energy_path = child / "energy_uj"
                log.debug(f"Path: {energy_path}")
                log.debug(f"Exists: {energy_path.exists()}")
                log.debug(f"Is file: {energy_path.is_file()}")
                # Change os.access to Path.exists() and Path.is_file(), and open with Path.open(), as it is more secure and reliable according to https://docs.python.org/3/library/os.html#os.access
                try:
                    energy_file = open(child / "energy_uj", "r")
                except Exception as e:
                    log.debug(f"Error opening file: {child / 'energy_uj'}")
                    log.debug(e)
                    continue
                log.debug(f"Opened file: {energy_file}")

                socket = match.groups()[0]
                with open(child / "name", "r") as file:
                    device_name = file.readline().strip()

                log.debug(device_name)

                if "dram" in device_name:
                    devType = DeviceType.RAM
                elif "package" in device_name:
                    devType = DeviceType.CPU
                # Ignoring psys interface until I get more data.
                # This paper might have no clue : https://dl.acm.org/doi/10.1145/3177754
                # elif "psys" in device_name:
                #     devType = DeviceType.CPU
                #     foundPsys = True
                else:
                    devType = DeviceType.OTHER

                if devType != DeviceType.OTHER:
                    with open(child / "max_energy_range_uj", "r") as file:
                        line = file.readline().strip()
                        max_energy = np.uint64(line)
                    dataType = MetricMetaData(
                        Unit.JOULE,
                        Magnitude.MICRO,
                        np.dtype("uint64"),
                        np.uint64(0),
                        max_energy,
                        max_energy,
                    )

                    log.debug(f"RAPL FILE OPENED: {energy_path}")
                    self._files.append(energy_file)
                    device = Sensor(
                        f"{devType.value}_{socket}_{device_name}",
                        devType,
                        self._metadata,
                        dataType,
                        getCallback(energy_file, str(energy_path)),
                    )

                    self.devices[device.id] = device
                    if "package" in device_name:
                        packageDevices.append(device)
                        packageFiles.append(energy_file)

                    for grandchild in child.iterdir():
                        match = re.match(SUBDIR_RGX, grandchild.name)
                        if match:
                            with open(grandchild / "name", "r") as file:
                                device_name = file.readline().strip()

                            if "dram" in device_name:
                                devType = DeviceType.RAM
                            elif "package" in device_name:
                                devType = DeviceType.CPU
                            # elif "psys" in device_name:
                            #     devType = DeviceType.CPU
                            #     foundPsys = True
                            else:
                                devType = DeviceType.OTHER

                            if devType != DeviceType.OTHER:
                                with open(
                                    grandchild / "max_energy_range_uj", "r"
                                ) as file:
                                    line = file.readline().strip()
                                    max_energy = np.uint64(line)

                                dataType = MetricMetaData(
                                    Unit.JOULE,
                                    Magnitude.MICRO,
                                    np.dtype("uint64"),
                                    np.uint64(0),
                                    max_energy,
                                    max_energy,
                                )

                                grandchild_energy_path = grandchild / "energy_uj"
                                energy_file = open(grandchild_energy_path, "r")
                                log.debug(f"RAPL FILE OPENED: {grandchild_energy_path}")
                                self._files.append(energy_file)
                                device = Sensor(
                                    f"{devType.value}_{socket}_{device_name}",
                                    devType,
                                    self._metadata,
                                    dataType,
                                    getCallback(
                                        energy_file, str(grandchild_energy_path)
                                    ),
                                )
                                log.debug(device)
                                self.devices[device.id] = device

                                if "package" in device_name:
                                    packageDevices.append(device)

        if foundPsys:
            for pkg, file in zip(packageDevices, packageFiles):
                log.info(f"Closing file: {file}")
                file.close()
                del self.devices[pkg.id]

        log.debug(
            f"Powercap RAPL devices {pp.pformat([deviceId for deviceId in self.devices])}"
        )

    def close(self) -> None:
        """Backend shutdown code (does nothing for intel rapl)."""
        log.debug("Closing files")
        for file in self._files:
            log.debug(f"Closing file: {file}")
            file.close()
        return

    def availableSensors(self) -> dict[str, tuple]:
        """Return string id set of visible devices.

        Returns
        -------
        set[str]
            Set with visible device ids.
        """
        return {
            sensor_id: (self.id, sensor.type, sensor.dataType.unit)
            for sensor_id, sensor in self.devices.items()
        }

    def getSensors(self, deviceList: set[str]) -> list[Sensor]:
        """Gather device objects based on a set of device ids.

        Parameters
        ----------
        deviceList : set[str]
            Set of device ids.

        Returns
        -------
        list[Sensor]
            Device objects.
        """
        return [self.devices[deviceId] for deviceId in deviceList]
