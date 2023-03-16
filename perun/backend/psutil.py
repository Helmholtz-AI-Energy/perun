"""psutil backend."""
from typing import Callable, List, Set

import numpy as np
import psutil

from perun import log
from perun.backend.backend import Backend, backend
from perun.data_model.measurement_type import Magnitude, MetricMetaData, Unit
from perun.data_model.sensor import DeviceType, Sensor


@backend
class PSUTILBackend(Backend):
    """PSUTIL Backend class."""

    name: str = "PSUTIL"
    description: str = "Obtain hardware data from psutil"

    def __init__(self) -> None:
        """Create psutil backend."""
        super().__init__()
        log.info("Init PSUTIL")

    def setup(self):
        """Configure psutil backend."""
        psutil.disk_io_counters.cache_clear()
        psutil.net_io_counters.cache_clear()
        self.metadata = {"source": f"psutil {psutil.__version__}"}

        for deviceName in self.visibleSensors():
            if deviceName == "RAM_USAGE":
                mem = psutil.virtual_memory()
                self.devices[deviceName] = Sensor(
                    deviceName,
                    DeviceType.RAM,
                    {"total": mem.total, "available": mem.available, **self.metadata},
                    MetricMetaData(
                        Unit.PERCENT,
                        Magnitude.ONE,
                        np.dtype("float32"),
                        np.float32(0),
                        np.float32(1.0),
                        np.float32(-1),
                    ),
                    self._getCallback(deviceName),
                )
            elif deviceName == "CPU_USAGE":
                self.devices[deviceName] = Sensor(
                    deviceName,
                    DeviceType.CPU,
                    {**self.metadata},
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
            elif "BYTES" in deviceName:
                self.devices[deviceName] = Sensor(
                    deviceName,
                    DeviceType.DISK if "DISK" in deviceName else DeviceType.NET,
                    {**self.metadata},
                    MetricMetaData(
                        Unit.BYTE,
                        Magnitude.ONE,
                        np.dtype("uint32"),
                        np.uint32(0),
                        np.uint32(np.iinfo("uint32").max),
                        np.uint32(np.iinfo("uint32").max),
                    ),
                    self._getCallback(deviceName),
                )

    def close(self):
        """Close backend."""
        pass

    def visibleSensors(self) -> Set[str]:
        """Return list of visible devices."""
        return {
            "RAM_USAGE",
            "CPU_USAGE",
            "DISK_READ_BYTES",
            "DISK_WRITE_BYTES",
            "NET_WRITE_BYTES",
            "NET_READ_BYTES",
        }

    def _getCallback(self, device: str) -> Callable[[], np.number]:
        """Return measuring function for each device."""
        if device == "RAM_USAGE":

            def func() -> np.number:
                return np.float32(psutil.virtual_memory().percent / 100)

        elif device == "CPU_USAGE":

            def func() -> np.number:
                return np.float32(psutil.cpu_percent())

        elif device == "DISK_READ_BYTES":

            def func() -> np.number:
                return np.uint32(psutil.disk_io_counters(nowrap=True).read_bytes)

        elif device == "DISK_WRITE_BYTES":

            def func() -> np.number:
                return np.uint32(psutil.disk_io_counters(nowrap=True).write_bytes)

        elif device == "NET_WRITE_BYTES":

            def func() -> np.number:
                return np.uint32(psutil.net_io_counters(nowrap=True).bytes_sent)

        elif device == "NET_READ_BYTES":

            def func() -> np.number:
                return np.uint32(psutil.net_io_counters(nowrap=True).bytes_recv)

        else:
            raise ValueError("Invalid device name")

        return func

    def getSensors(self, deviceList: Set[str]) -> List[Sensor]:
        """Return desired device objects."""
        return [self.devices[deviceName] for deviceName in deviceList]


PSUTILBackend()
