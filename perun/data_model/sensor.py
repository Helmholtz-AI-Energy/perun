"""Device module."""

import enum
from dataclasses import asdict, dataclass
from typing import Any, Callable

from perun.data_model.measurement_type import MetricMetaData, Number


class DeviceType(str, enum.Enum):
    """DeviceType enum."""

    RACK = "rack"
    NODE = "node"
    CPU = "cpu"
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
        """Read value from sensor."""
        return self.measureCallback()

    def toDict(self) -> dict[str, Any]:
        """Return device as a dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "metadata": self.metadata,
            "dataType": asdict(self.dataType),
        }
