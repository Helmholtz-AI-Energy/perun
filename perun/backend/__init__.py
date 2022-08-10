"""Backend module.

Defines backends and devices used for energy measurements. Connects to different backends and provides a unified interface for them.
"""
# flake8: noqa
from .backend import backends, Backend
from .device import Device
from . import intel_rapl
from . import nvml

__all__ = ["backends", "Device", "Backend"]
