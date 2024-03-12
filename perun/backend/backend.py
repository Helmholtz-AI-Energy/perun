"""Backend module."""

import logging
from abc import abstractmethod
from typing import Dict, List, Set

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
        log.info(f"Initialized {self.name} backend")

    @abstractmethod
    def visibleSensors(self) -> Set[str]:
        """Get a string id of devices visible by the backend."""
        pass

    @abstractmethod
    def getSensors(self, deviceList: Set[str]) -> List[Sensor]:
        """Return device objects based on the provided list of device ids.

        :param deviceList: List with wanted device ids
        :type deviceList: Set[str]
        :return: List of device objects
        :rtype: List[Sensor]
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
