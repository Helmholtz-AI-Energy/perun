"""Util module."""
import os
from datetime import datetime
from pathlib import Path

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


def getRunName(app: Path) -> str:
    """Return application name based on configuration and application path.

    Parameters
    ----------
    app : Path
        Application path.

    Returns
    -------
    str
        Application name.
    """
    app_name = config.get("output", "app_name")

    if app_name and app_name != "SLURM":
        return app_name
    elif app_name and "SBATCH_JOB_NAME" in os.environ and app_name == "SLURM":
        return os.environ["SBATCH_JOB_NAME"]
    elif isinstance(app, Path):
        return app.stem


def getRunId(starttime: datetime) -> str:
    """Return run id based on the configuration object or the current datetime.

    Parameters
    ----------
    starttime : datetime
        Datetime object

    Returns
    -------
    str
        Run id.
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
