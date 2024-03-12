"""Util module."""

import logging
import os
import re
from datetime import datetime
from typing import Dict, List, Set

from perun import config

log = logging.getLogger("perun")


class Singleton(type):
    """
    Metaclass for creating singleton classes.

    Singleton classes are classes that can only have one instance. This metaclass
    ensures that only one instance of a class is created and provides a way to
    access that instance.

    Attributes
    ----------
    _instances : dict
        A dictionary that stores the instances of the singleton classes. The keys
        are the singleton classes and the values are the corresponding instances.
    __allow_reinitialization : bool
        A flag that indicates whether the singleton class allows reinitialization.
        If set to True, the `__call__` method will reinitialize the instance if the
        class has already been instantiated.

    Methods
    -------
    __call__(*args, **kwargs)
        Overrides the default behavior of calling the class. It ensures that only one
        instance of the class is created and returns that instance.

    Examples
    --------
    >>> class MyClass(metaclass=Singleton):
    ...     pass
    ...
    >>> my_instance = MyClass()  # Returns the instance of MyClass
    """

    _instances: Dict = {}
    __allow_reinitialization: bool = False

    def __call__(cls, *args, **kwargs):
        """
        Call method for the singleton class.

        This method is called when the singleton class is invoked as a function.
        It ensures that only one instance of the class is created and returned.

        Parameters
        ----------
        cls : class object
            The class object.
        *args : tuple
            Variable length argument list.
        **kwargs : dict
            Arbitrary keyword arguments.

        Returns
        -------
        instance : object
            The instance of the singleton class.

        Examples
        --------
        >>> instance = MyClass()
        >>> instance()
        <MyClass object at 0x7f9a8a3d6a90>
        """
        if cls not in cls._instances:
            log.debug(f"Singleton __call__ {cls.__name__}")
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        else:
            instance = cls._instances[cls]
            if (
                hasattr(cls, "__allow_reinitialization")
                and cls.__allow_reinitialization
            ):
                # if the class allows reinitialization, then do it
                log.debug(f"Singleton __call__ {cls.__name__} reinit")
                instance.__init__(*args, **kwargs)  # call the init again

        log.debug(
            f"Singleton __call__ {cls.__name__} returning instance id {id(instance)}"
        )
        return instance


def getRunId(starttime: datetime) -> str:
    """
    Return run id based on the configuration object or the current datetime.

    Parameters
    ----------
    starttime : datetime
        The datetime object representing the start time of the run.

    Returns
    -------
    str
        The run id.

    Notes
    -----
    If the configuration object has a valid run id specified, it will be returned.
    If the run id is set to "SLURM" and the environment variable "SLURM_JOB_ID" is present,
    the value of "SLURM_JOB_ID" will be returned.
    Otherwise, the ISO formatted string representation of the start time will be returned.
    """
    run_id = config.get("output", "run_id")
    if run_id and run_id != "SLURM":
        return run_id
    elif (
        run_id
        and "SLURM_JOB_ID" in os.environ
        and config.get("output", "run_id") == "SLURM"
    ):
        return os.environ["SLURM_JOB_ID"]
    else:
        return starttime.isoformat()


def increaseIdCounter(existing: List[str], newId: str) -> str:
    """Increase id counter based on number of existing entries with the same id.

    Parameters
    ----------
    existing : List[str]
        List of existing ids.
    newId : str
        New id to compare againts.

    Returns
    -------
    str
        newId with an added counter if any matches were found.
    """
    exp = re.compile(r"^" + newId + r"(_\d+)?$")
    count = len(list(filter(lambda x: exp.match(x), existing)))
    return newId + f"_{count}" if count > 0 else newId


def printableSensorConfiguration(
    sensors_config: List[Dict[str, Set[str]]], host_rank: Dict[str, List[int]]
) -> str:
    """Create string with the available backends and sensors in each node.

    Parameters
    ----------
    sensors_config : List[Dict[str, Set[str]]]
        Perun Sensor configuration
    host_rank : Dict[str, List[int]]
        Perun Host Rank mapping

    Returns
    -------
    str
        String to print for the sensors CLI subcommand.
    """
    configString: str = ""
    for rank, bes in enumerate(sensors_config):
        configString += f"Rank: {rank}\n"
        for key in sorted(bes.keys()):
            items = bes[key]
            if len(items) > 0:
                configString += f"   {key}:\n"

                for device in sorted(items):
                    configString += f"       {device}\n"
                configString += "\n"

    configString += "Hostnames:\n"
    for host, ranks in host_rank.items():
        configString += f"   {host}: {ranks}\n"

    return configString
