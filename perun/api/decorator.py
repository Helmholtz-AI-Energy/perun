"""Decorator module."""

import functools
import logging
from typing import Any, Callable, Optional

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

log = logging.getLogger(__name__)


def monitor(region_name: Optional[str] = None) -> Callable:
    """Decorate function to monitor its energy usage."""

    def inner_function(func: Callable) -> Callable:
        @functools.wraps(func)
        def func_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get custom config and kwargs
            region_id = region_name if region_name else func.__name__

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
    """Decorate function to monitor its energy usage."""

    def inner_function(func: Callable) -> Callable:
        @functools.wraps(func)
        def func_wrapper(*args: Any, **kwargs: Any) -> Any:
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
    perun = Perun.getInstance()
    if func.__name__ not in perun.postprocess_callbacks:
        log.info(f"Rank {perun.comm.Get_rank()}: Registering callback {func.__name__}")
        perun.postprocess_callbacks[func.__name__] = func
