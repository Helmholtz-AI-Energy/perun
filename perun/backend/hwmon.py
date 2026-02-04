"""Defines Linux Hardware Monitoring (hwmon) backend classes."""

import logging
import pprint as pp
import re
from io import IOBase
from pathlib import Path
from typing import Callable

import numpy as np

from perun.backend.backend import Backend
from perun.data_model.measurement_type import Magnitude, MetricMetaData, Number, Unit
from perun.data_model.sensor import DeviceType, Sensor

log = logging.getLogger(__name__)

HWMON_PATH = "/sys/class/hwmon/"

# Regex patterns for device subdirectory power sensors
POWER_AVERAGE_RGX = r"power(\d+)_average"  # Power average in microwatts


class HWMonBackend(Backend):
    """Hardware Monitoring (hwmon) backend for reading system sensors.

    Uses the Linux hwmon sysfs interface to gather power measurements
    from device subdirectories.
    """

    id = "hwmon"
    name = "Hardware Monitor"
    description = "Reads power measurements from hwmon sysfs device subdirectories"

    def setup(self) -> None:
        """Initialize hwmon backend and discover available sensors."""
        self._files: list[IOBase] = []
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

        def get_sensor_label(hwmon_dir: Path, sensor_type: str, index: str) -> str:
            """Get the label for a sensor if available."""
            label_path = hwmon_dir / f"{sensor_type}{index}_label"
            if label_path.exists():
                return read_file_content(label_path)
            return ""

        def get_sensor_max(hwmon_dir: Path, sensor_type: str, index: str) -> int | None:
            """Get the maximum value for a sensor if available."""
            max_path = hwmon_dir / f"{sensor_type}{index}_max"
            if max_path.exists():
                try:
                    return int(read_file_content(max_path))
                except ValueError:
                    return None
            return None

        def get_sensor_min(hwmon_dir: Path, sensor_type: str, index: str) -> int | None:
            """Get the minimum value for a sensor if available."""
            min_path = hwmon_dir / f"{sensor_type}{index}_min"
            if min_path.exists():
                try:
                    return int(read_file_content(min_path))
                except ValueError:
                    return None
            return None

        # Iterate over all hwmon devices
        for hwmon_dir in sorted(hwmonPath.iterdir()):
            if not hwmon_dir.is_dir():
                continue

            hwmon_name = hwmon_dir.name
            log.debug(f"Scanning hwmon device: {hwmon_dir}")

            # Get the device name
            name_path = hwmon_dir / "name"
            device_name = (
                read_file_content(name_path) if name_path.exists() else hwmon_name
            )

            # Store metadata about this hwmon device
            self._metadata[hwmon_name] = device_name

            log.debug(f"Device name: {device_name}")

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

                        # Get label from standard label file if oem_info not available
                        label = (
                            oem_info
                            if oem_info
                            else get_sensor_label(device_dir, "power", sensor_index)
                        )

                        # Get limits if available
                        max_val = get_sensor_max(device_dir, "power", sensor_index)
                        min_val = get_sensor_min(device_dir, "power", sensor_index)

                        # Determine device type based on label
                        dev_type = DeviceType.OTHER
                        label_lower = label.lower()
                        if (
                            "cpu" in label_lower
                            or "core" in label_lower
                            or "processor" in label_lower
                        ):
                            dev_type = DeviceType.CPU
                        elif "gpu" in label_lower or "graphics" in label_lower:
                            dev_type = DeviceType.GPU
                        elif "memory" in label_lower or "dram" in label_lower:
                            dev_type = DeviceType.RAM

                        # Create sensor ID
                        label_part = label if label else f"power{sensor_index}_avg"
                        sensor_id = (
                            f"{device_name}_{hwmon_name}_device_power_{label_part}"
                        )
                        # Clean up sensor ID (remove spaces, special chars)
                        sensor_id = re.sub(r"[^\w\-_]", "_", sensor_id)

                        # Create metadata for this sensor (power_average is in microwatts)
                        dataType = MetricMetaData(
                            Unit.WATT,
                            Magnitude.MICRO,
                            np.dtype("int64"),
                            np.int64(min_val) if min_val is not None else np.int64(0),
                            np.int64(max_val) if max_val is not None else np.int64(0),
                            np.int64(0),  # overflow value
                        )

                        sensor_metadata = {
                            "hwmon_device": hwmon_name,
                            "device_name": device_name,
                            "sensor_type": "power_average",
                            "sensor_index": sensor_index,
                            "label": label,
                            "oem_info": oem_info,
                        }

                        device = Sensor(
                            sensor_id,
                            dev_type,
                            sensor_metadata,
                            dataType,
                            getCallback(sensor_file_handle, str(sensor_path)),
                        )

                        self.devices[device.id] = device
                        log.debug(f"Added device power sensor: {sensor_id}")

        log.debug(
            f"HWMon devices: {pp.pformat([deviceId for deviceId in self.devices])}"
        )

    def close(self) -> None:
        """Backend shutdown code, closes all open sensor files."""
        log.debug("Closing hwmon sensor files")
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
