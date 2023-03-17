"""Decorator module."""

import functools

from perun import config, log
from perun.configuration import read_custom_config, save_to_config
from perun.perun import monitor_application


def monitor(
    configuration: str = "./.perun.ini",
    **conf_kwargs,
):
    """Decorate function to monitor its energy usage."""

    def inner_function(func):
        @functools.wraps(func)
        def func_wrapper(*args, **kwargs):
            # Get custom config and kwargs

            read_custom_config(None, None, configuration)
            for key, value in conf_kwargs.items():
                save_to_config(key, value)

            log.setLevel(config.get("debug", "log_lvl"))
            func_result = monitor_application(func, args, kwargs)

            return func_result

        return func_wrapper

    return inner_function
