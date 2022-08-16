"""Backend module.

Defines backends and devices used for energy measurements. Connects to different backends and provides a unified interface for them.
"""
from . import intel_rapl, nvml

# flake8: noqa
from .backend import Backend, backends
from .device import Device

__all__ = ["backends", "Device", "Backend"]
