"""psutil backend."""

from typing import Callable, List, Set

import numpy as np
import psutil

from perun.backend.backend import Backend
from perun.data_model.measurement_type import Magnitude, MetricMetaData, Unit
from perun.data_model.sensor import DeviceType, Sensor


class PSUTILBackend(Backend):
    """PSUTIL Backend class."""

    id: str = "psutil"
    name: str = "PSUTIL"
    description: str = "Obtain hardware data from psutil"

    def __init__(self) -> None:
        """Create psutil backend."""
        super().__init__()

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
                    {
                        "total": str(mem.total),
                        "available": str(mem.available),
                        **self.metadata,
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
                        np.dtype("uint64"),
                        np.uint64(0),
                        np.uint64(np.iinfo("uint64").max),
                        np.uint64(np.iinfo("uint64").max),
                    ),
                    self._getCallback(deviceName),
                )

    def close(self):
        """Close backend."""
        pass

    def visibleSensors(self) -> Set[str]:
        """Return list of visible devices."""
        sensors = {
            "RAM_USAGE",
            "CPU_USAGE",
            "NET_WRITE_BYTES",
            "NET_READ_BYTES",
        }
        if psutil.disk_io_counters(nowrap=True) is not None:
            sensors.add("DISK_READ_BYTES")
            sensors.add("DISK_WRITE_BYTES")
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

        else:
            raise ValueError("Invalid device name")

        return func

    def getSensors(self, deviceList: Set[str]) -> List[Sensor]:
        """Return desired device objects."""
        return [self.devices[deviceName] for deviceName in deviceList]
