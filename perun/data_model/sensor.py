"""Device module."""
import enum
from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict

import numpy as np

from perun.data_model.measurement_type import MetricMetaData


class DeviceType(enum.Enum):
    """DeviceType enum."""

    OTHER = "OTHER"
    CPU = "CPU"
    GPU = "GPU"
    RAM = "RAM"
    DISK = "DISK"
    NET = "NET"
    NODE = "NODE"
    RACK = "RACK"
    FAN = "FAN"


@dataclass
class Sensor:
    """Defines a devices sensor properties."""

    id: str
    type: DeviceType
    metadata: Dict
    dataType: MetricMetaData
    measureCallback: Callable[[], np.number]

    def read(self) -> np.number:
        """Read value from sensor."""
        return self.measureCallback()

    def toDict(self) -> Dict[str, Any]:
        """Return device as a dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "metadata": self.metadata,
            "dataType": asdict(self.dataType),
        }
