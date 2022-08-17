"""Device module."""
from dataclasses import dataclass
from typing import Callable, Any, Dict
from perun.units import Unit


@dataclass
class Device:
    """Defines a devices sensor properties."""

    id: str
    long_name: str
    unit: Unit
    mag: str
    measureCallback: Callable[[], float]

    def read(self) -> float:
        """Read value from sensor."""
        return self.measureCallback()

    def toDict(self) -> Dict[str, Any]:
        """Return device as a dictionary."""
        return {
            "id": self.id,
            "long_name": self.long_name,
            "unit": self.unit,
            "mag": self.mag,
        }
