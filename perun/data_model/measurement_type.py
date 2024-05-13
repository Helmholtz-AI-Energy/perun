"""Unit module."""

import dataclasses
import enum
import logging
from typing import Dict

import numpy as np

log = logging.getLogger("perun")


class Unit(str, enum.Enum):
    """Unit enum."""

    JOULE = "J"
    WATT = "W"
    BYTE = "B"
    SECOND = "s"
    PERCENT = "%"
    SCALAR = ""
    GRAM = "g"
    HZ = "Hz"

    @property
    def symbol(self) -> str:
        """Symbol associated with Unit.

        Returns
        -------
        str
            Unit symbol string.
        """
        return self.value

    def __str__(self) -> str:
        """Convert object to string."""
        return self.symbol


_mag_symbols: Dict[str, str] = {
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


class Magnitude(float, enum.Enum):
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

    @classmethod
    def fromSymbol(cls, symbol: str):
        """Create a Magniture objet from a magnigure symbol.

        Parameters
        ----------
        symbol : str
            Magnigure symbol string.

        Returns
        -------
        _type_
            Magniture Enum object.

        Raises
        ------
        ValueError
            If an invalid symbol is given.
        """
        for key, value in _mag_symbols.items():
            if value == symbol:
                return cls[key]
        msg = f"Magnitude symbol {symbol} does not exist."
        log.error(msg)
        raise ValueError(msg)

    @property
    def symbol(self) -> str:
        """Symbol associated with magnitude prefix.

        Returns
        -------
        str
            String symbol
        """
        return _mag_symbols[self.name]

    def __str__(self) -> str:
        """Convert object to string."""
        return self.symbol


@dataclasses.dataclass
class MetricMetaData:
    """Collects a metric metadata."""

    unit: Unit
    mag: Magnitude
    dtype: np.dtype
    min: np.number
    max: np.number
    fill: np.number

    @classmethod
    def fromDict(cls, mdDict: Dict):
        """Create MetricMetadata from a dictionary."""
        dtype = np.dtype(mdDict["dtype"])
        return cls(
            Unit(mdDict["unit"]),
            Magnitude(mdDict["mag"]),
            dtype,
            dtype.type(mdDict["min"]),
            dtype.type(mdDict["max"], dtype=dtype),
            dtype.type(mdDict["fill"], dtype=dtype),
        )

    def copy(self):
        """Copy MetricMetaData object.

        Returns
        -------
        _type_
            Copy of object.
        """
        return MetricMetaData(
            Unit(self.unit.value),
            Magnitude(self.mag.value),
            self.dtype,
            self.min.copy(),
            self.max.copy(),
            self.fill.copy(),
        )
