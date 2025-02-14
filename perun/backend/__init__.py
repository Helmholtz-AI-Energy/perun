"""Backend module."""

from typing import Dict, Type

from .backend import Backend
from .nvml import NVMLBackend
from .powercap_rapl import PowercapRAPLBackend
from .psutil import PSUTILBackend
from .rocmsmi import ROCMBackend
from .util import getBackendMetadata, getHostMetadata

available_backends: Dict[str, Type[Backend]] = {
    "NVMLBackend": NVMLBackend,
    "PowercapRAPLBackend": PowercapRAPLBackend,
    "PSUTILBackend": PSUTILBackend,
    "ROCMBackend": ROCMBackend,
}

__all__ = ["getBackendMetadata", "getHostMetadata"]
