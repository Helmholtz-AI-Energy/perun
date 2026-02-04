"""psutil backend."""

import logging
from typing import Callable, Dict, List, Set, Tuple

import numpy as np
import psutil

from perun.backend.backend import Backend
from perun.data_model.measurement_type import Magnitude, MetricMetaData, Number, Unit
from perun.data_model.sensor import DeviceType, Sensor

log = logging.getLogger(__name__)


class PSUTILBackend(Backend):
    """PSUTIL Backend class."""

    id: str = "psutil"
    name: str = "PSUTIL"
    description: str = "Obtain hardware data from psutil"

    def setup(self) -> None:
        """Configure psutil backend."""
        psutil.disk_io_counters.cache_clear()  # type: ignore[attr-defined]
        psutil.net_io_counters.cache_clear()  # type: ignore[attr-defined]
        self._metadata = {"source": f"psutil {psutil.__version__}"}
        self._sensors = self._findSensors()

    def close(self) -> None:
        """Close backend."""
        pass

    def _findSensors(self) -> Dict[str, Tuple]:
        """Return list of visible devices.

        Returns
        -------
        Dict[str, Tuple]
            Dictionary with device ids and measurement unit.
        """
        sensors = {}

        if psutil.virtual_memory().used is not None:
            mem = psutil.virtual_memory()
            sensors["RAM_USAGE"] = (self.id, DeviceType.RAM, Unit.BYTE)
            self._metadata["total_ram_byte"] = str(mem.total)
            self._metadata["available_ram_byte"] = str(mem.available)
        else:
            log.info("RAM_USAGE not available")

        if psutil.cpu_percent(percpu=True) is not None:
            for cpu_id, _ in enumerate(psutil.cpu_percent(percpu=True)):
                sensors[f"CPU_USAGE_{cpu_id}"] = (self.id, DeviceType.CPU, Unit.PERCENT)
        else:
            log.info("CPU_USAGE not available")
        if psutil.net_io_counters(nowrap=True) is not None:
            for nid in psutil.net_if_addrs().keys():
                sensors[f"NET_WRITE_BYTES_{nid}"] = (self.id, DeviceType.NET, Unit.BYTE)
                sensors[f"NET_READ_BYTES_{nid}"] = (self.id, DeviceType.NET, Unit.BYTE)

        if psutil.disk_io_counters(nowrap=True) is not None:
            for disk in psutil.disk_io_counters(perdisk=True).keys():
                sensors[f"DISK_READ_BYTES_{disk}"] = (self.id, DeviceType.DISK, Unit.BYTE)
                sensors[f"DISK_WRITE_BYTES_{disk}"] = (self.id, DeviceType.DISK, Unit.BYTE)

        if psutil.cpu_freq(percpu=True) is not None:
            for cpu_id, _ in enumerate(psutil.cpu_freq(percpu=True)):
                sensors[f"CPU_FREQ_{cpu_id}"] = (self.id, DeviceType.CPU, Unit.HZ)
        return sensors

    def availableSensors(self) -> Dict[str, Tuple]:
        """Return a dictionary with all available sensors.

        Returns
        -------
        Dict[str, Tuple]
            Dictionary with device ids and measurement unit.
        """
        return self._sensors

    def _getCallback(self, device: str) -> Callable[[], Number]:
        """Return measuring function for each device."""
        if device == "RAM_USAGE":

            def func() -> Number:
                return np.uint64(psutil.virtual_memory().used)

        elif device.startswith("CPU_USAGE_"):
            cpuId = int(device.split("_")[-1])

            def func() -> Number:
                return np.float32(psutil.cpu_percent(percpu=True)[cpuId])

        elif device.startswith("DISK_READ_BYTES_"):
            disk_id = device.split("_")[-1]

            def func() -> Number:
                return np.uint64(psutil.disk_io_counters(perdisk=True, nowrap=True)[disk_id].read_bytes)  # type: ignore[union-attr]

        elif device.startswith("DISK_WRITE_BYTES_"):
            disk_id = device.split("_")[-1]

            def func() -> Number:
                return np.uint64(psutil.disk_io_counters(perdisk=True, nowrap=True)[disk_id].write_bytes)  # type: ignore[union-attr]

        elif device.startswith("NET_WRITE_BYTES_"):
            nid = device.split("_")[-1]

            def func() -> Number:
                return np.uint64(psutil.net_io_counters(pernic=True, nowrap=True)[nid].bytes_sent)

        elif device.startswith("NET_READ_BYTES_"):
            nid = device.split("_")[-1]

            def func() -> Number:
                return np.uint64(psutil.net_io_counters(pernic=True, nowrap=True)[nid].bytes_recv)

        elif device.startswith("CPU_FREQ_"):
            cpuId = int(device.split("_")[-1])

            def func() -> Number:
                return np.float32(psutil.cpu_freq(percpu=True)[cpuId].current)

        else:
            raise ValueError("Invalid device name")

        return func

    def getSensors(self, deviceList: Set[str]) -> List[Sensor]:
        """Return desired device objects."""
        devices = []
        for deviceName in deviceList:
            if deviceName == "RAM_USAGE":
                mem = psutil.virtual_memory()
                devices.append(
                    Sensor(
                        deviceName,
                        DeviceType.RAM,
                        {
                            "total": str(mem.total),
                            "available": str(mem.available),
                            **self._metadata,
                        },
                        MetricMetaData(
                            Unit.BYTE,
                            Magnitude.ONE,
                            np.dtype("uint64"),
                            np.uint64(0),
                            np.uint64(np.iinfo("uint64").max),
                            np.uint64(np.iinfo("uint64").max),
                        ),
                        self._getCallback(deviceName),
                    )
                )
            elif "CPU_USAGE" in deviceName:
                devices.append(
                    Sensor(
                        deviceName,
                        DeviceType.CPU,
                        {**self._metadata},
                        MetricMetaData(
                            Unit.PERCENT,
                            Magnitude.ONE,
                            np.dtype("float32"),
                            np.float32(0),
                            np.float32(100.0),
                            np.float32(-1),
                        ),
                        self._getCallback(deviceName),
                    )
                )
            elif "BYTES" in deviceName:
                devices.append(
                    Sensor(
                        deviceName,
                        DeviceType.DISK if "DISK" in deviceName else DeviceType.NET,
                        {**self._metadata},
                        MetricMetaData(
                            Unit.BYTE,
                            Magnitude.ONE,
                            np.dtype("uint64"),
                            np.uint64(0),
                            np.uint64(np.iinfo("uint64").max),
                            np.uint64(np.iinfo("uint64").max),
                        ),
                        self._getCallback(deviceName),
                    )
                )
            elif "CPU_FREQ" in deviceName:
                id = int(deviceName.split("_")[-1])
                devices.append(
                    Sensor(
                        deviceName,
                        DeviceType.CPU,
                        {**self._metadata},
                        MetricMetaData(
                            Unit.HZ,
                            Magnitude.MEGA,
                            np.dtype("float32"),
                            np.float32(psutil.cpu_freq(percpu=True)[id].min),
                            np.float32(psutil.cpu_freq(percpu=True)[id].max),
                            np.float32(0),
                        ),
                        self._getCallback(deviceName),
                    )
                )
        return devices
