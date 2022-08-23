"""Unit module."""
from perun import log


class MagnitudePrefix:
    """Quick conversion from metric symbols and prefixes."""

    symbols = ["p", "n", "µ", "m", "", "k", "M", "G", "T"]
    prefixes = ["pico", "nano", "micro", "mili", "", "kilo", "mega", "giga", "tera"]
    factor = [1e-12, 1e-9, 1e-6, 1e-3, 1, 1e3, 1e6, 1e9, 1e12]

    @classmethod
    def getFactor(cls, prefixOrSymbol: str) -> float:
        """Return magnitude factor based on prefix/symbol string.

        Args:
            prefixOrSymbol (str): Either a metrix prefix (ex. "mili", "giga") or symbol (ex. "m", "G")

        Raises:
            ValueError: In case prefix/symbol does not exist

        Returns:
            float: Magnitude factor as a float
        """
        if prefixOrSymbol in cls.symbols:
            idx = cls.symbols.index(prefixOrSymbol)
            return cls.factor[idx]
        elif prefixOrSymbol in cls.prefixes:
            idx = cls.prefixes.index(prefixOrSymbol)
            return cls.factor[idx]
        else:
            log.error("Invalid magnitude prefix")
            raise ValueError(prefixOrSymbol)

    @classmethod
    def getSymbol(cls, prefix: str) -> str:
        """Return symbol based on metric prefix.

        Args:
            prefix (str): Metrix prefix (ex. "mili", "tera")

        Raises:
            ValueError: In case prefix/symbol does not exist

        Returns:
            str: Metric symbol
        """
        if prefix in cls.prefixes:
            idx = cls.prefixes.index(prefix)
            return cls.symbols[idx]
        else:
            log.error("Invalid magniture prefix")
            raise ValueError(prefix)

    @classmethod
    def transformFactor(cls, fromPrefix: str, toPrefix: str) -> float:
        """
        Obtain multiplication factor to transform unit between 2 prefixes.

        Args:
            fromPrefix (str): Current magnitude prefix
            toPrefix (str): Desired magnitude prefix

        Returns:
            float: Transformation factor
        """
        fromFactor = cls.getFactor(fromPrefix)
        toFactor = cls.getFactor(toPrefix)
        return fromFactor / toFactor


class Unit:
    """Metrix unit attributes and helper methods."""

    symbol: str = "#"
    name: str = "Scalar"

    @classmethod
    def toString(cls, value: float, mag: str = None):
        """Return string value with magnitude prefix and unit symbol."""
        magSymbol = MagnitudePrefix.getSymbol(mag) if mag else ""
        return f"{value:.3f}{magSymbol}{cls.symbol}"


class Joule(Unit):
    """Joule unit class."""

    symbol: str = "J"
    name: str = "Joule"

    KWH_factor = 3.6 * 1e6

    @classmethod
    def to_kWh(cls, value: float) -> float:
        """Transform from Joules to kWh."""
        return value / cls.KWH_factor

    @classmethod
    def from_kWh(cls, kwh: float) -> float:
        """Transform from kWh to Joules."""
        return kwh * cls.KWH_factor


class Watt(Unit):
    """Watt unit class."""

    symbol: str = "W"
    name: str = "Watt"


class Second(Unit):
    """Second unit class."""

    symbol: str = "s"
    name: str = "Second"
