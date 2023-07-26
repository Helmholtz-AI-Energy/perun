import platform
from typing import Any, Dict, Set

from perun import log


def getHostMetadata(backendConfig: Dict[str, Set[str]]) -> Dict[str, Any]:
    """Return dictionary with the full system metadata based on the provided backend configuration.

    :param backendConfig: Sensor backend configuration to include in the metadata object.
    :type backendConfig: Dict[str, Set[str]]
    :return: Dictionary with system metadata
    :rtype: Dict[str, Any]
    """
    from perun.backend import backends

    metadata = {}
    for name, method in platform.__dict__.items():
        if callable(method):
            try:
                metadata[name] = method()
            except Exception as e:
                log.warn(f"platform method {name} did not work")
                log.warn(e)

    metadata["backends"] = {}
    for backend in backends:
        if backend.name in backendConfig:
            metadata["backends"][backend.name] = {}
            sensors = backend.getSensors(backendConfig[backend.name])
            for sensor in sensors:
                metadata["backends"][backend.name][sensor.id] = sensor.metadata

    return metadata
