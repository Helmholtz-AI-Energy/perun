"""Backend util."""
import platform
from typing import Any, Dict, Set

from perun import log
from perun.backend import Backend


def getHostMetadata(
    backends: Dict[str, Backend], backendConfig: Dict[str, Set[str]]
) -> Dict[str, Any]:
    """Return dictionary with the full system metadata based on the provided backend configuration.

    Parameters
    ----------
    backends : List[Backend]
        List with available backends.
    backendConfig : Dict[str, Set[str]]
        Sensor backend configuration to include in the metadata object.

    Returns
    -------
    Dict[str, Any]
        Dictionary with host metadata.
    """
    metadata = {}
    for name, method in platform.__dict__.items():
        if callable(method):
            try:
                metadata[name] = method()
            except Exception as e:
                log.warn(f"platform method {name} did not work")
                log.warn(e)

    metadata["backends"] = {}
    for backend in backends.values():
        if backend.name in backendConfig:
            metadata["backends"][backend.name] = {}
            sensors = backend.getSensors(backendConfig[backend.name])
            for sensor in sensors:
                metadata["backends"][backend.name][sensor.id] = sensor.metadata

    return metadata
