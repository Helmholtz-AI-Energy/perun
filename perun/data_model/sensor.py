"""Device module."""

import enum
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any

from perun.data_model.measurement_type import MetricMetaData, Number


class DeviceType(enum.StrEnum):
    """DeviceType enum."""

    RACK = "rack"
    NODE = "node"
    SOCKET = "socket"
    CPU = "cpu"
    SYSIO = "sysio"
    GPU = "gpu"
    RAM = "ram"
    DISK = "disk"
    NET = "net"
    FAN = "fan"
    OTHER = "other"


@dataclass
class Sensor:
    """Defines a devices sensor properties."""

    id: str
    type: DeviceType
    metadata: dict
    dataType: MetricMetaData
    measureCallback: Callable[[], Number]

    def read(self) -> Number:
        """Read value from sensor.

        Returns
        -------
        Number
            Current sensor value.
        """
        return self.measureCallback()

    def toDict(self) -> dict[str, Any]:
        """Return device as a dictionary.

        Returns
        -------
        dict[str, Any]
            Dictionary representation of the sensor.
        """
        return {
            "id": self.id,
            "type": self.type.value,
            "metadata": self.metadata,
            "dataType": asdict(self.dataType),
        }
