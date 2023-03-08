"""Unit module."""
import dataclasses
import enum
from typing import Dict

import numpy as np


class Unit(enum.Enum):
    """Unit enum."""

    JOULE = "J"
    WATT = "W"
    BYTE = "B"
    SECOND = "s"
    PERCENT = "%"

    def symbol(self) -> str:
        """Symbol associated with Unit.

        Returns:
            str: String with unit symbol.
        """
        return self.value

    def __str__(self) -> str:
        """Convert object to string."""
        return self.symbol()


class Magnitude(enum.Enum):
    """Magnitude prefix enum."""

    PICO = 1e-12
    NANO = 1e-9
    MICRO = 1e-6
    MILI = 1e-3
    ONE = 1
    KILO = 1e3
    MEGA = 1e6
    GIGA = 1e9
    TERA = 1e12

    def symbol(self) -> str:
        """Symbol associated with magnitude prefix.

        Returns:
            str: String with magnitude symbol.
        """
        _symbols: Dict = {
            "PICO": "p",
            "NANO": "n",
            "MICRO": "µ",
            "MILI": "m",
            "ONE": "",
            "KILO": "k",
            "MEGA": "M",
            "GIGA": "G",
            "TERA": "T",
        }
        return _symbols[self.value]

    def __str__(self) -> str:
        """Convert object to string."""
        return self.symbol()


@dataclasses.dataclass
class MeasurementType:
    """Collects a measurements metadata."""

    unit: Unit
    mag: Magnitude
    dtype: np.dtype
    min: np.number
    max: np.number
    fill: np.number
