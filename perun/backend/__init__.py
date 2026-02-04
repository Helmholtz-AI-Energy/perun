"""Backend module."""

from typing import Type

from .backend import Backend
from .hwmon_grace import HWMonGraceBackend
from .nvml import NVMLBackend
from .powercap_rapl import PowercapRAPLBackend
from .psutil import PSUTILBackend
from .rocmsmi import ROCMBackend

available_backends: dict[str, Type[Backend]] = {
    "HWMonBackend": HWMonGraceBackend,
    "NVMLBackend": NVMLBackend,
    "PowercapRAPLBackend": PowercapRAPLBackend,
    "PSUTILBackend": PSUTILBackend,
    "ROCMBackend": ROCMBackend,
}
