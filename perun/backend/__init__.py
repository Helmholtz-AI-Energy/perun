"""Backend module."""

from typing import Type

from .backend import Backend
from .hwmon import HWMonBackend
from .nvml import NVMLBackend
from .powercap_rapl import PowercapRAPLBackend
from .psutil import PSUTILBackend
from .rocmsmi import ROCMBackend

available_backends: dict[str, Type[Backend]] = {
    "HWMonBackend": HWMonBackend,
    "NVMLBackend": NVMLBackend,
    "PowercapRAPLBackend": PowercapRAPLBackend,
    "PSUTILBackend": PSUTILBackend,
    "ROCMBackend": ROCMBackend,
}
