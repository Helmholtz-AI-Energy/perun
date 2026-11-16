"""Decorator module."""

import functools
import logging
from typing import Any, Callable

from perun.configuration import (
    config,
    read_custom_config,
    read_environ,
    sanitize_config,
    save_to_config,
)
from perun.core import Perun
from perun.data_model.data import DataNode
from perun.logging import set_logger_config
from perun.monitoring.application import Application
from perun.processing import Number

log = logging.getLogger(__name__)


def monitor(region_name: str | None = None) -> Callable:
    """Decorate function to monitor its energy usage.

    Parameters
    ----------
    region_name : str | None, optional
        Name of the monitored region, by default the name of the decorated function.

    Returns
    -------
    Callable
        Decorator that wraps the function in a monitored region.
    """

    def inner_function(func: Callable) -> Callable:
        """Wrap ``func`` in a monitored region.

        Parameters
        ----------
        func : Callable
            Function to monitor.

        Returns
        -------
        Callable
            Wrapped function.
        """

        @functools.wraps(func)
        def func_wrapper(*args: Any, **kwargs: Any) -> Any:
            """Run ``func`` and record its start and end as region events.

            Parameters
            ----------
            *args : Any
                Positional arguments passed to ``func``.
            **kwargs : Any
                Keyword arguments passed to ``func``.

            Returns
            -------
            Any
                Result of ``func``.
            """
            # Get custom config and kwargs
            region_id = region_name if region_name else func.__name__  # ty: ignore[missing-attribute]

            perun = Perun(config)
            if perun.warmup_round:
                func_result = func(*args, **kwargs)
            else:
                log.info(f"Rank {perun.comm.Get_rank()}: Entering '{region_id}'")
                perun.mark_event(region_id)
                func_result = func(*args, **kwargs)
                perun.mark_event(region_id)
                log.info(f"Rank {perun.comm.Get_rank()}: Leaving '{region_id}'")

            return func_result

        return func_wrapper

    return inner_function


def perun(configuration_file: str = "./.perun.ini", **conf_kwargs: Any) -> Callable:
    """Decorate function to monitor its energy usage.

    Parameters
    ----------
    configuration_file : str, optional
        Path to a perun configuration file, by default "./.perun.ini".
    **conf_kwargs : Any
        Configuration options that override the values in the configuration file.

    Returns
    -------
    Callable
        Decorator that runs the function under perun's monitoring.
    """

    def inner_function(func: Callable) -> Callable:
        """Wrap ``func`` so it runs under perun's monitoring.

        Parameters
        ----------
        func : Callable
            Function to monitor.

        Returns
        -------
        Callable
            Wrapped function.
        """

        @functools.wraps(func)
        def func_wrapper(*args: Any, **kwargs: Any) -> Any:
            """Configure perun and monitor a call to ``func``.

            Parameters
            ----------
            *args : Any
                Positional arguments passed to ``func``.
            **kwargs : Any
                Keyword arguments passed to ``func``.

            Returns
            -------
            Any
                Result of ``func``.
            """
            # 1) Read custom config
            read_custom_config(configuration_file)

            # 2) Read environment variables
            read_environ()

            # 3) Parse remaining arguments
            for key, value in conf_kwargs.items():
                save_to_config(key, value)

            sanitize_config(config)
            set_logger_config(config)

            app = Application(func, config, args=args, kwargs=kwargs)
            perun = Perun(config)

            func_result = perun.monitor_application(app)

            return func_result

        return func_wrapper

    return inner_function


def register_callback(func: Callable[[DataNode], None]) -> None:
    """Register a function to run after perun has finished collection data.

    Parameters
    ----------
    func : Callable[[DataNode], None]
        Function to be called.
    """
    perun: Perun | None = Perun.getInstance()
    func_name: str = func.__name__  # ty: ignore[missing-attribute]

    if perun and func_name not in perun._postprocess_callbacks:
        log.info(f"Rank {perun.comm.Get_rank()}: Registering callback {func_name}")
        perun._postprocess_callbacks[func_name] = func


def register_live_callback(
    obj: Callable[[], Callable[[dict[str, Number]], None]],
    id: str,
) -> None:
    """
    Register a function that initializes a live callback function that will be run after each datapoint is collected on the monitoring subprocess.

    This is useful for live monitoring of metrics in real-time.

    The function passed should return a callable that accepts the metric identifier and the metric value.

    This structure is for systems that need to establish a connection to an external server, like MLFlow and Weights and Biases, as such objects are not serializable and can sometimes cause issues with the multiprocessing module.

    Parameters
    ----------
    obj : Callable[[], Callable[[str, Union[int, float]], None]]
        Function that initializes the live callback.
        It should return a callable that accepts the metric identifier and the metric value. It should take no arguments.
    id : str
        Identifier for the live callback, used to register it in the Perun instance.
    """
    perun: Perun | None = Perun.getInstance()
    if perun and id not in perun._live_callbacks:
        log.info(f"Rank {perun.comm.Get_rank()}: Registering live callback {id}")
        perun._live_callbacks[id] = obj
