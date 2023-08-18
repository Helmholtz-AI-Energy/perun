"""Decorator module."""
import functools
from typing import Optional

from perun import log
from perun.perun import Perun


def monitor(region_name: Optional[str] = None):
    """Decorate function to monitor its energy usage."""

    def inner_function(func):
        @functools.wraps(func)
        def func_wrapper(*args, **kwargs):
            # Get custom config and kwargs
            region_id = region_name if region_name else func.__name__

            perun = Perun()  # type: ignore

            log.info(f"Rank {perun.comm.Get_rank()}: Entering '{region_id}'")
            perun.local_regions.addEvent(region_id)  # type: ignore
            func_result = func(*args, **kwargs)
            perun.local_regions.addEvent(region_id)  # type: ignore
            log.info(f"Rank {perun.comm.Get_rank()}: Leaving '{region_id}'")

            return func_result

        return func_wrapper

    return inner_function
