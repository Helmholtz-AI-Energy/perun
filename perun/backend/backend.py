"""Backend module."""
from abc import ABC, abstractmethod

import functools
from .device import Device
from perun import log


class Backend(ABC):
    """Abstract backend class."""

    name: str = "Abstract backend class"
    description: str = "Abstract backend class description"

    def __init__(self) -> None:
        """Import and setup backend."""
        super().__init__()
        self.devices: list[Device] = []
        self.setup()

    @abstractmethod
    def visibleDevices(self) -> set[str]:
        """Get a string id of devices visible by the backend."""
        pass

    @abstractmethod
    def getDevices(self, deviceList: set[str]) -> list[Device]:
        """
        Return device objects based on the provided list of device ids.

        Args:
            deviceList (set[str]): List with wanted device ids

        Returns:
            list[Device]: List of device objects
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


backends: list[Backend] = []


def backend(cls):
    """Backend class decorator.

    Marks a class a singleton, and if setup succeeds,
    gets added to the backends list.
    """

    @functools.wraps(cls)
    def backend_wrapper(*args, **kwargs):
        if not backend_wrapper.instance:
            try:
                backend_wrapper.instance = cls(*args, **kwargs)
                backends.append(backend_wrapper.instance)
            except ImportError as ie:
                log.debug(f"Missing dependencies for backend {cls.__name__}")
                log.debug(ie)
            except Exception as e:
                log.debug(f"Unknown error loading dependecy {cls.__name__}")
                log.debug(e)

    backend_wrapper.instance = None
    return backend_wrapper
