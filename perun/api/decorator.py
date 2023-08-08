"""Decorator module."""
import functools
from typing import Optional

from perun import config, log
from perun.perun import Perun


def monitor(region_name: Optional[str] = None):
    """Decorate function to monitor its energy usage."""

    def inner_function(func):
        @functools.wraps(func)
        def func_wrapper(*args, **kwargs):
            # Get custom config and kwargs
            region_id = region_name if region_name else func.__name__

            perun = Perun(config)

            log.info(f"Rank {perun.comm.Get_rank()}: Entered  '{region_id}'")
            func_result = func(*args, **kwargs)
            log.info(f"Rank {perun.comm.Get_rank()}: Exited '{region_id}'")
            return func_result

        return func_wrapper

    return inner_function
