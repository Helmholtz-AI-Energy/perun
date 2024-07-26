"""Backend util."""

import logging
import platform
from typing import Any, Dict, Tuple

from perun.backend.backend import Backend

log = logging.getLogger("perun")


def getHostMetadata() -> Dict[str, Any]:
    """Return dictionary with the platform related metadata.

    Returns
    -------
    Dict[str, Any]
        Dictionary with host metadata.
    """
    metadata = {}
    for name, method in platform.__dict__.items():
        if callable(method):
            try:
                value = method()
                if isinstance(value, tuple):
                    value = " ".join(value)
                value = value.strip()
                if value != "":
                    metadata[name] = value
            except Exception as e:
                log.debug(f"platform method {name} did not work")
                log.debug(e)

    return metadata


def getBackendMetadata(
    backends: Dict[str, Backend], sensors: Dict[str, Tuple[str]]
) -> Dict[str, Any]:
    """Get backend related metadata dictionary based on the current sensor configuration.

    Parameters
    ----------
    backends : List[Backend]
        List with available backends.
    backendConfig : Dict[str, Set[str]]
        Sensor backend configuration to include in the metadata object.

    Returns
    -------
    Dict[str, Any]
        Backend metadata dictionary.
    """
    backend_metadata: Dict[str, Any] = {}
    for _, sensor_md in sensors.items():
        backend = backends[sensor_md[0]]
        if backend.name not in backend_metadata:
            backend_metadata[backend.name] = backend.metadata

    return backend_metadata
