"""Device module."""
import enum
from dataclasses import dataclass
from typing import Any, Callable, Dict

import numpy as np

from perun.data_model.measurement_type import MeasurementType


class DeviceType(enum.Enum):
    """DeviceType enum."""

    OTHER = "OTHER"
    CPU = "CPU"
    GPU = "GPU"
    RAM = "RAM"
    STORAGE = "STORAGE"
    NETWORK = "NET"
    NODE = "NODE"
    RACK = "RACK"
    FAN = "FAN"


@dataclass
class Sensor:
    """Defines a devices sensor properties."""

    id: str
    type: DeviceType
    metadata: Dict
    dataType: MeasurementType
    measureCallback: Callable[[], np.number]

    def read(self) -> np.number:
        """Read value from sensor."""
        return self.measureCallback()

    def toDict(self) -> Dict[str, Any]:
        """Return device as a dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "metadata": self.metadata,
            "dataType": self.dataType,
        }
