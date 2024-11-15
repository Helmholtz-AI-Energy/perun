"""Util module."""

import logging
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

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
    matches: List[re.Match] = list(
        filter(lambda m: isinstance(m, re.Match), map(lambda x: exp.match(x), existing))  # type: ignore
    )
    if len(matches) > 0:
        existing_idxs = list(
            sorted(map(lambda m: int(m.group(1)[1:]) if m.group(1) else 0, matches))
        )
        highest_idx = existing_idxs[-1]
        return newId + f"_{highest_idx + 1}"
    else:
        return newId


def filter_sensors(
    sensors: Dict[str, Tuple],
    include_sensors: Optional[List[str]] = None,
    exclude_sensors: Optional[List[str]] = None,
    include_backends: Optional[List[str]] = None,
    exclude_backends: Optional[List[str]] = None,
) -> Dict[str, Tuple]:
    """Filter sensors based on include and exclude lists.

    Parameters
    ----------
    sensors : Dict[str, Tuple]
        Dictionary of sensors.
    include_sensors : Optional[List[str]], optional
        List of sensors to include, by default None
    exclude_sensors : Optional[List[str]], optional
        List of sensors to exclude, by default None
    include_backends : Optional[List[str]], optional
        List of backends to include, by default None
    exclude_backends : Optional[List[str]], optional
        List of backends to exclude, by default None

    Returns
    -------
    Dict[str, Tuple]
        Filtered dictionary of sensors.
    """
    # Ensure only include or excluce lists are set

    if include_sensors and exclude_sensors:
        log.warning(
            "Both include and exclude sensors options are set. Defaulting to exclude only."
        )
        include_sensors = None

    if include_backends and exclude_backends:
        log.warning(
            "Both include and exclude backends options are set. Defaulting to exclude only."
        )
        include_backends = None

    # If all are None, return all sensors
    if not any([include_sensors, exclude_sensors, include_backends, exclude_backends]):
        return sensors

    # Ensure exlude and include lists are unique
    if include_sensors:
        include_sensors = list(set(include_sensors))
        log.debug(f"Include sensors: {include_sensors}")
    if exclude_sensors:
        exclude_sensors = list(set(exclude_sensors))
        log.debug(f"Exclude sensors: {exclude_sensors}")
    if include_backends:
        include_backends = list(set(include_backends))
        log.debug(f"Include backends: {include_backends}")
    if exclude_backends:
        exclude_backends = list(set(exclude_backends))
        log.debug(f"Exclude backends: {exclude_backends}")

    # Filter sensors based on include and exclude lists
    filtered_sensors = {}
    for sensor_name, sensor in sensors.items():
        backend = sensor[0]

        if include_backends:
            if not matchesOneOf(include_backends, backend):
                continue
        if exclude_backends:
            if matchesOneOf(exclude_backends, backend):
                continue
        if include_sensors:
            if not matchesOneOf(include_sensors, sensor_name):
                continue
        if exclude_sensors:
            if matchesOneOf(exclude_sensors, sensor_name):
                continue
        filtered_sensors[sensor_name] = sensor

    # If no sensors were matched, log a warning
    if not filtered_sensors:
        log.warning("No sensors matched the include and exclude filters.")

    return filtered_sensors


def matchesOneOf(patterns: List[str], string: str) -> bool:
    """Check if a string matches any of the given patterns.

    Parameters
    ----------
    patterns : List[str]
        List of patterns to match against.
    string : str
        String to check.

    Returns
    -------
    bool
        True if the string matches any of the patterns, False otherwise.
    """
    for pattern in patterns:
        if re.match(pattern, string):
            return True
    return False
