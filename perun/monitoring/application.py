"""Application module."""

import gc
import logging
import logging.handlers
import os
import subprocess
from configparser import ConfigParser
from pathlib import Path
from typing import Any, Callable, Dict, Union

log = logging.getLogger("perun")


class Application:
    """
    Represents an application to be executed.

    Parameters
    ----------
    app : Union[Path, Callable]
        The application to be executed. It can be either a file path or a callable object.
    config : ConfigParser
        The configuration object containing application settings.
    args : tuple, optional
        Positional arguments to be passed to the application (default is an empty tuple).
    kwargs : Dict, optional
        Keyword arguments to be passed to the application (default is an empty dictionary).

    Attributes
    ----------
    name : str
        The name of the application.
    args : tuple
        The positional arguments to be passed to the application.
    kwargs : Dict
        The keyword arguments to be passed to the application.

    Methods
    -------
    run()
        Executes the application.
    """

    def __init__(
        self,
        app: Union[Path, Callable, str],
        config: ConfigParser,
        is_binary: bool = False,
        args: tuple = (),
        kwargs: Dict = {},
    ):
        self._app = app
        self._name = self._setName(config)
        self._args = args
        self._kwargs = kwargs
        self._is_binary = is_binary
        if isinstance(app, Path):
            try:
                with open(app, "r") as scriptFile:
                    self._scriptFile = scriptFile.read()
            except FileNotFoundError:
                log.error(
                    f"perun could not find the file {app}. Please check the path."
                )
                exit()

    @property
    def name(self):
        """Return the application name."""
        return self._name

    @property
    def args(self):
        """Return the application positional arguments."""
        return self._args

    @property
    def kwargs(self):
        """Return the application keyword arguments."""
        return self._kwargs

    @property
    def is_binary(self):
        """Return the application keyword arguments."""
        return self._is_binary

    def _setName(self, config: ConfigParser) -> str:
        """
        Return the application name based on the configuration and application path.

        Parameters
        ----------
        config : ConfigParser
            The configuration object containing application settings.

        Returns
        -------
        str
            The application name.
        """
        app_name = config.get("output", "app_name")

        if app_name and app_name != "SLURM":
            return app_name
        elif (
            app_name
            and app_name != "SLURM"
            and "SBATCH_JOB_NAME" in os.environ
            and app_name == "SLURM"
        ):
            return os.environ["SBATCH_JOB_NAME"]
        elif isinstance(self._app, Path):
            return self._app.stem
        elif callable(self._app):
            return self._app.__name__
        elif isinstance(self._app, str):
            return self._app
        else:
            raise ValueError("Application name not found")

    def _cleanup(self):
        for i in range(3):
            gc.collect(i)

    def run(self) -> Any:
        """
        Execute the application. If callable, returns the function result.

        Raises
        ------
        ValueError
            If the application is not found.
        """
        if self._is_binary and isinstance(self._app, str):
            subprocess.run([self._app, *self._args], env=os.environ)
        elif isinstance(self._app, Path):
            exec(
                self._scriptFile,
                {"__name__": "__main__", "__file__": self.name},
            )
            self._cleanup()
        elif callable(self._app):
            result = self._app(*self._args, **self._kwargs)
            self._cleanup()
            return result
        else:
            raise ValueError("Application not found")

    def __str__(self):
        """Return the application name."""
        return f"{self.name}"

    def __repr__(self):
        """Return the application name."""
        return f"Application({self.name})"
