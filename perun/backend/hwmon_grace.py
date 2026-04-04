"""Defines Linux Hardware Monitoring (hwmon) backend classes."""

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

HWMON_PATH = "/sys/class/hwmon/"

# Regex patterns for device subdirectory power sensors
POWER_AVERAGE_RGX = r"power(\d+)_average$"  # Power average in microwatts


class HWMonGraceBackend(Backend):
    """Hardware Monitoring (hwmon) backend for reading system sensors.

    Uses the Linux hwmon sysfs interface to gather power measurements
    from device subdirectories.

    Docs: https://docs.nvidia.com/dccpu/grace-perf-tuning-guide/power-thermals.html
    """

    id = "hwmon-grace"
    name = "Hardware Monitor (Grace)"
    description = "Reads power measurements from hwmon sysfs device subdirectories for Grace systems."

    def setup(self) -> None:
        """Initialize hwmon backend and discover available sensors."""
        self._files: list[IOBase] = []

        cpuInfo = cpuinfo.get_cpu_info()
        self._metadata = {}
        for key, value in cpuInfo.items():
            if value is not None and value != "":
                self._metadata[key] = str(value)

        self.devices: dict[str, Sensor] = {}
        log.debug(f"CPU info metadata: {pp.pformat(self._metadata)}")

        self._metadata: dict[str, str] = {}
        self.devices: dict[str, Sensor] = {}

        hwmonPath = Path(HWMON_PATH)

        if not hwmonPath.exists():
            raise ImportWarning("No hwmon interface available")

        def getCallback(file: IOBase, file_path: str) -> Callable[[], Number]:
            """Create a callback function to read sensor value from file."""

            def func() -> Number:
                try:
                    file.seek(0)
                    value = file.readline().strip()
                    return np.int64(value) if value else np.int64(0)
                except Exception as e:
                    log.warning(f"Error reading file: {file_path}")
                    log.exception(e)
                    return np.int64(0)

            return func

        def read_file_content(path: Path) -> str:
            """Read content from a sysfs file."""
            try:
                with open(path, "r") as f:
                    return f.readline().strip()
            except Exception:
                return ""

        # Iterate over all hwmon devices
        for hwmon_dir in sorted(hwmonPath.iterdir()):
            if not hwmon_dir.is_dir():
                continue

            hwmon_name = hwmon_dir.name
            log.debug(f"Scanning hwmon device: {hwmon_dir}")

            # Store metadata about this hwmon device

            # Scan for power*_average files in device subdirectories
            device_dir = hwmon_dir / "device"
            if device_dir.exists() and device_dir.is_dir():
                log.debug(f"Scanning device subdirectory: {device_dir}")
                for sensor_file in device_dir.iterdir():
                    match = re.match(POWER_AVERAGE_RGX, sensor_file.name)
                    if match:
                        sensor_index = match.group(1)
                        sensor_path = sensor_file

                        log.debug(f"Found power_average sensor: {sensor_path}")

                        try:
                            sensor_file_handle = open(sensor_path, "r")
                        except Exception as e:
                            log.debug(f"Error opening file: {sensor_path}")
                            log.debug(e)
                            continue

                        self._files.append(sensor_file_handle)

                        # Get device name from power*_oem_info file
                        oem_info_path = device_dir / f"power{sensor_index}_oem_info"
                        oem_info = (
                            read_file_content(oem_info_path)
                            if oem_info_path.exists()
                            else ""
                        )

                        # Determine device type based on label
                        if "Module Power Socket" in oem_info:
                            device_type = DeviceType.OTHER
                        elif "Grace Power Socket" in oem_info:
                            device_type = DeviceType.SOCKET
                        elif "CPU Power Socket" in oem_info:
                            device_type = DeviceType.CPU
                        elif "SysIO Power Socket" in oem_info:
                            device_type = DeviceType.SYSIO
                        else:
                            device_type = DeviceType.OTHER

                        # Create sensor ID
                        sensor_id = f"{oem_info.replace(' ', '_').lower()}"

                        # Create metadata for this sensor (power_average is in microwatts)
                        dataType = MetricMetaData(
                            Unit.WATT,
                            Magnitude.MICRO,
                            np.dtype("int64"),
                            np.int64(0),
                            np.iinfo("int64").max,
                            np.int64(0),  # overflow value
                        )

                        sensor_metadata = {
                            "hwmon_device": hwmon_name,
                            "device_name": oem_info,
                            "sensor_type": "power_average",
                        }

                        device = Sensor(
                            sensor_id,
                            device_type,
                            sensor_metadata,
                            dataType,
                            getCallback(sensor_file_handle, str(sensor_path)),
                        )

                        self.devices[device.id] = device
                        log.debug(f"Added device power sensor: {sensor_id}")

        log.info(
            f"HWMon devices: {pp.pformat([deviceId for deviceId in self.devices])}"
        )

    def close(self) -> None:
        """Backend shutdown code, closes all open sensor files."""
        log.debug("Closing hwmon sensor files")
        for file in self._files:
            log.debug(f"Closing file: {file}")
            file.close()
        return

    def availableSensors(self) -> dict[str, tuple[str, DeviceType, Unit]]:
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
