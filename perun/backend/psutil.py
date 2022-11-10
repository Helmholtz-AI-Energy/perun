"""psutil backend."""
from typing import Callable, List, Set

import numpy as np
import psutil

from perun import config, log
from perun.backend.backend import Backend, backend
from perun.backend.device import Device
from perun.units import Byte, Percent


@backend
class PSUTIL(Backend):
    """PSUTIL Backend class."""

    name: str = "PSUTIL"
    description: str = "Obtain hardware data from psutil"

    def __init__(self) -> None:
        """Create psutil backend."""
        super().__init__()
        log.info("Init PSUTIL")

    def setup(self):
        """Configure psutil backend."""
        self.total_ram = psutil.virtual_memory().total / 1024.0**3  # byte
        self.conversion_factor = config.getfloat("devices", "ram2watt")

    def close(self):
        """Close backend."""
        pass

    def visibleDevices(self) -> Set[str]:
        """Return list of visible devices."""
        return {
            "RAM_USAGE",
            "CPU_USAGE",
            "DISK_READ_BYTES",
            "DISK_WRITE_BYTES",
            "NET_SENT_BYTES",
            "NET_RECV_BYTES",
        }

    def _getCallback(self, device: str) -> Callable[[], np.number]:
        """Return measuring function for each device."""
        if device == "RAM_USAGE":

            def func() -> np.number:
                return np.float32(psutil.virtual_memory().percent / 100)

        elif device == "CPU_USAGE":

            def func() -> np.number:
                return np.float64(psutil.cpu_percent())

        elif device == "DISK_READ_BYTES":

            def func() -> np.number:
                return np.uint64(psutil.disk_io_counters().read_bytes)

        elif device == "DISK_WRITE_BYTES":

            def func() -> np.number:
                return np.uint64(psutil.disk_io_counters().write_bytes)

        elif device == "NET_SENT_BYTES":

            def func() -> np.number:
                return np.uint64(psutil.net_io_counters().bytes_sent)

        elif device == "NET_RECV_BYTES":

            def func() -> np.number:
                return np.uint64(psutil.net_io_counters().bytes_recv)

        else:
            raise ValueError("Invalid device name")

        return func

    def getDevices(self, deviceList: Set[str]) -> List[Device]:
        """Return desired device objects."""
        for device in deviceList:
            if device == "RAM_USAGE":
                self.devices.append(
                    Device(
                        device,
                        f"{device}_psutil",
                        Percent(),
                        "",
                        np.float32(0),
                        np.float32(1.0),
                        "float32",
                        self._getCallback(device),
                    )
                )
            elif device == "CPU_USAGE":
                self.devices.append(
                    Device(
                        device,
                        f"{device}_psutil",
                        Percent(),
                        "",
                        np.float32(0),
                        np.float32(1.0),
                        "float32",
                        self._getCallback(device),
                    )
                )
            elif device == "DISK_READ_BYTES":
                self.devices.append(
                    Device(
                        device,
                        f"{device}_psutil",
                        Byte(),
                        "",
                        np.uint64(0),
                        np.uint64(np.iinfo("uint64").max),
                        "uint64",
                        self._getCallback(device),
                    )
                )
            elif device == "DISK_WRITE_BYTES":
                self.devices.append(
                    Device(
                        device,
                        f"{device}_psutil",
                        Byte(),
                        "",
                        np.uint64(0),
                        np.uint64(np.iinfo("uint64").max),
                        "uint64",
                        self._getCallback(device),
                    )
                )
            elif device == "NET_SENT_BYTES":
                self.devices.append(
                    Device(
                        device,
                        f"{device}_psutil",
                        Byte(),
                        "",
                        np.uint64(0),
                        np.uint64(np.iinfo("uint64").max),
                        "uint64",
                        self._getCallback(device),
                    )
                )

            elif device == "NET_RECV_BYTES":
                self.devices.append(
                    Device(
                        device,
                        f"{device}_psutil",
                        Byte(),
                        "",
                        np.uint64(0),
                        np.uint64(np.iinfo("uint64").max),
                        "uint64",
                        self._getCallback(device),
                    )
                )
        return self.devices


PSUTIL()
