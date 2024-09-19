"""psutil backend."""

import logging
from typing import Callable, Dict, List, Set, Tuple

import numpy as np
import psutil

from perun.backend.backend import Backend
from perun.data_model.measurement_type import Magnitude, MetricMetaData, Unit
from perun.data_model.sensor import DeviceType, Sensor

log = logging.getLogger("perun")


class PSUTILBackend(Backend):
    """PSUTIL Backend class."""

    id: str = "psutil"
    name: str = "PSUTIL"
    description: str = "Obtain hardware data from psutil"

    def setup(self):
        """Configure psutil backend."""
        psutil.disk_io_counters.cache_clear()
        psutil.net_io_counters.cache_clear()
        self._metadata = {"source": f"psutil {psutil.__version__}"}

    def close(self):
        """Close backend."""
        pass

    def availableSensors(self) -> Dict[str, Tuple]:
        """Return list of visible devices.

        Returns
        -------
        Dict[str, Tuple]
            Dictionary with device ids and measurement unit.
        """
        sensors = {}

        if psutil.virtual_memory().used is not None:
            sensors["RAM_USAGE"] = (self.id, DeviceType.RAM, Unit.BYTE)
        else:
            log.info("RAM_USAGE not available")

        if psutil.cpu_percent() is not None:
            sensors["CPU_USAGE"] = (self.id, DeviceType.CPU, Unit.PERCENT)
        else:
            log.info("CPU_USAGE not available")

        if psutil.net_io_counters(nowrap=True) is not None:
            sensors["NET_WRITE_BYTES"] = (self.id, DeviceType.NET, Unit.BYTE)
            sensors["NET_READ_BYTES"] = (self.id, DeviceType.NET, Unit.BYTE)

        if psutil.disk_io_counters(nowrap=True) is not None:
            sensors["DISK_READ_BYTES"] = (self.id, DeviceType.DISK, Unit.BYTE)
            sensors["DISK_WRITE_BYTES"] = (self.id, DeviceType.DISK, Unit.BYTE)

        if psutil.cpu_freq(percpu=True) is not None:
            for cpu_id, _ in enumerate(psutil.cpu_freq(percpu=True)):
                sensors[f"CPU_FREQ_{cpu_id}"] = (self.id, DeviceType.CPU, Unit.HZ)
        return sensors

    def _getCallback(self, device: str) -> Callable[[], np.number]:
        """Return measuring function for each device."""
        if device == "RAM_USAGE":

            def func() -> np.number:
                return np.uint64(psutil.virtual_memory().used)

        elif device == "CPU_USAGE":

            def func() -> np.number:
                return np.float32(psutil.cpu_percent())

        elif device == "DISK_READ_BYTES":

            def func() -> np.number:
                return np.uint64(psutil.disk_io_counters(nowrap=True).read_bytes)  # type: ignore

        elif device == "DISK_WRITE_BYTES":

            def func() -> np.number:
                return np.uint64(psutil.disk_io_counters(nowrap=True).write_bytes)  # type: ignore

        elif device == "NET_WRITE_BYTES":

            def func() -> np.number:
                return np.uint64(psutil.net_io_counters(nowrap=True).bytes_sent)

        elif device == "NET_READ_BYTES":

            def func() -> np.number:
                return np.uint64(psutil.net_io_counters(nowrap=True).bytes_recv)

        elif device.startswith("CPU_FREQ_"):
            cpuId = int(device.split("_")[-1])

            def func() -> np.number:
                return np.float32(psutil.cpu_freq(percpu=True)[cpuId].current)  # type: ignore

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
            elif deviceName == "CPU_USAGE":
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
                            np.float32(psutil.cpu_freq(percpu=True)[id].min),  # type: ignore
                            np.float32(psutil.cpu_freq(percpu=True)[id].max),  # type: ignore
                            np.float32(0),
                        ),
                        self._getCallback(deviceName),
                    )
                )
        return devices
