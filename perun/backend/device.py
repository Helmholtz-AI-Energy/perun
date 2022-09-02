"""Device module."""
from dataclasses import dataclass
from typing import Any, Callable, Dict

import numpy as np

from perun.units import Unit


@dataclass
class Device:
    """Defines a devices sensor properties."""

    id: str
    long_name: str
    unit: Unit
    mag: str
    min: np.number
    max: np.number
    dtype: str
    measureCallback: Callable[[], np.number]

    def read(self) -> np.number:
        """Read value from sensor."""
        return self.measureCallback()

    def toDict(self) -> Dict[str, Any]:
        """Return device as a dictionary."""
        return {
            "id": self.id,
            "long_name": self.long_name,
            "unit": self.unit,
            "mag": self.mag,
            "min": self.min,
            "max": self.max,
            "dtype": self.dtype,
        }
