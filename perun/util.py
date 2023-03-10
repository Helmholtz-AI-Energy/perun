"""Util module."""
import os
from datetime import datetime
from pathlib import Path
from typing import Callable, Union

from perun import config


def getRunName(app: Union[Path, Callable]) -> str:
    """Return application name based on available info.

    Args:
        app (Union[Path, Callable]): The path or function that is being monitored.

    Returns:
        str: Application name.
    """
    if config.get("output", "app_name"):
        return config.get("output", "app_name")
    elif "SBATCH_JOB_NAME" in os.environ:
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
    if config.get("output", "run_id"):
        return config.get("output", "run_id")
    elif "SLURM_JOB_ID" in os.environ:
        return os.environ["SLURM_JOB_ID"]
    else:
        return startime.isoformat()
