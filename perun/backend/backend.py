"""Backend module."""

import logging
from abc import abstractmethod
from typing import Dict, List, Set, Tuple

from perun.util import Singleton

from ..data_model.sensor import Sensor

log = logging.getLogger("perun")


class Backend(metaclass=Singleton):
    """Abstract backend class."""

    id: str = "abstract_backend"
    name: str = "Abstract backend class"
    description: str = "Abstract backend class description"

    def __init__(self) -> None:
        """Import and setup backend."""
        super().__init__()
        self.devices: Dict = {}
        self.setup()
        self._metadata: Dict = {}
        log.info(f"Initialized {self.name} backend")

    @property
    def metadata(self) -> Dict:
        """Return backend metadata."""
        return self._metadata

    @abstractmethod
    def availableSensors(self) -> Dict[str, Tuple]:
        """Return a dictionary with all available sensors. Each entry contains the backend id and type of sensor.

        Returns
        -------
        Dict[Tuple[str]]
            Dictionary with device ids and measurement unit.
        """
        pass

    @abstractmethod
    def getSensors(self, deviceList: Set[str]) -> List[Sensor]:
        """
        Return device objects based on the provided list of device ids.

        Parameters
        ----------
        deviceList : Set[str]
            List with wanted device ids

        Returns
        -------
        List[Sensor]
            List of device objects
        """
        pass

    @abstractmethod
    def close(self):
        """Clean up and close backend related activities."""
        pass

    @abstractmethod
    def setup(self):
        """Perform backend setup."""
        pass
