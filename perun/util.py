"""Util module."""
import os
from datetime import datetime
from pathlib import Path
from typing import Callable, Union

from perun import config


def singleton(class_):
    """Singleton decorator.

    Parameters
    ----------
    class_ : _type_
        Class to decorate as singleton

    Returns
    -------
    _type_
        Decoreated class definition
    """
    instances = {}

    def getinstance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]

    return getinstance


def getRunName(app: Union[Path, Callable]) -> str:
    """Return application name based on available info.

    Args:
        app (Union[Path, Callable]): The path or function that is being monitored.

    Returns:
        str: Application name.
    """
    app_name = config.get("output", "app_name")

    if app_name and app_name != "SLURM":
        return config.get("output", "app_name")
    elif app_name and "SBATCH_JOB_NAME" in os.environ and app_name == "SLURM":
        return os.environ["SBATCH_JOB_NAME"]
    elif isinstance(app, Path):
        return app.stem
    else:
        return app.__name__


def getRunId(startime: datetime) -> str:
    """Get run id from available info.

    Args:
        startime (datetime): Time when application was started.

    Returns:
        str: String id.
    """
    run_id = config.get("output", "run_id")
    if run_id and run_id != "SLURM":
        return config.get("output", "run_id")
    elif (
        run_id
        and "SLURM_JOB_ID" in os.environ
        and config.get("output", "run_id") == "SLURM"
    ):
        return os.environ["SLURM_JOB_ID"]
    else:
        return startime.isoformat()
