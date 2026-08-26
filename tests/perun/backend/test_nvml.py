"""Unit tests for the NVML (NVIDIA) backend using a fake ``pynvml`` module.

The backend imports ``pynvml`` lazily via ``importlib.import_module``. We inject
a fake module into ``sys.modules`` so the backend can be exercised without an
NVIDIA GPU or the real bindings installed.
"""

import sys
import types

import numpy as np
import pytest

from perun.data_model.measurement_type import Unit
from perun.data_model.sensor import DeviceType


class _NVMLError(Exception):
    pass


class _NVMLErrorUninitialized(_NVMLError):
    pass


class _MemoryInfo:
    def __init__(self, total, used):
        self.total = total
        self.used = used


def _make_fake_pynvml(device_count=2, power=150000, mem_used=1024, mem_total=8192):
    """Build a minimal fake ``pynvml`` module driving the NVML backend."""
    mod = types.ModuleType("pynvml")

    mod.NVMLError = _NVMLError
    mod.NVMLError_Uninitialized = _NVMLErrorUninitialized
    mod.NVML_CLOCK_SM = 0
    mod.NVML_CLOCK_MEM = 1
    mod.NVML_CLOCK_GRAPHICS = 2

    state = {"init_calls": 0, "shutdown_calls": 0}
    mod._state = state

    def nvmlInit():
        state["init_calls"] += 1

    def nvmlShutdown():
        state["shutdown_calls"] += 1

    def nvmlDeviceGetCount():
        return device_count

    def nvmlSystemGetCudaDriverVersion():
        return 12040

    def nvmlSystemGetDriverVersion():
        return "550.00"

    def nvmlDeviceGetHandleByIndex(i):
        if i >= device_count:
            raise _NVMLError(f"no device {i}")
        return {"index": i}

    def nvmlDeviceGetPowerUsage(handle):
        return power

    def nvmlDeviceGetMemoryInfo(handle):
        return _MemoryInfo(mem_total, mem_used)

    def nvmlDeviceGetClockInfo(handle, clock_id):
        return 1000 + clock_id

    def nvmlDeviceGetMaxClockInfo(handle, clock_id):
        return 2000 + clock_id

    def nvmlDeviceGetUUID(handle):
        return f"GPU-uuid-{handle['index']}"

    def nvmlDeviceGetName(handle):
        return f"FakeGPU{handle['index']}"

    def nvmlDeviceGetPowerManagementDefaultLimit(handle):
        return 300000

    mod.nvmlInit = nvmlInit
    mod.nvmlShutdown = nvmlShutdown
    mod.nvmlDeviceGetCount = nvmlDeviceGetCount
    mod.nvmlSystemGetCudaDriverVersion = nvmlSystemGetCudaDriverVersion
    mod.nvmlSystemGetDriverVersion = nvmlSystemGetDriverVersion
    mod.nvmlDeviceGetHandleByIndex = nvmlDeviceGetHandleByIndex
    mod.nvmlDeviceGetPowerUsage = nvmlDeviceGetPowerUsage
    mod.nvmlDeviceGetMemoryInfo = nvmlDeviceGetMemoryInfo
    mod.nvmlDeviceGetClockInfo = nvmlDeviceGetClockInfo
    mod.nvmlDeviceGetMaxClockInfo = nvmlDeviceGetMaxClockInfo
    mod.nvmlDeviceGetUUID = nvmlDeviceGetUUID
    mod.nvmlDeviceGetName = nvmlDeviceGetName
    mod.nvmlDeviceGetPowerManagementDefaultLimit = (
        nvmlDeviceGetPowerManagementDefaultLimit
    )
    return mod


@pytest.fixture()
def fake_pynvml(monkeypatch, setup_cleanup):
    mod = _make_fake_pynvml()
    monkeypatch.setitem(sys.modules, "pynvml", mod)
    return mod


@pytest.fixture()
def backend(fake_pynvml):
    from perun.backend.nvml import NVMLBackend

    b = NVMLBackend()
    yield b
    b.close()


def test_setup_metadata(backend):
    md = backend.metadata
    assert md["source"] == "Nvidia Managment Library"
    assert "cuda_version" in md
    assert "driver_version" in md


def test_available_sensors_power_mem_clocks(backend):
    sensors = backend.availableSensors()
    # 2 devices * (power + mem + 3 clocks) = 10 sensors.
    assert len(sensors) == 2 * 5
    assert "CUDA:0_POWER" in sensors
    assert "CUDA:0_MEM" in sensors
    assert any(k.startswith("CUDA:0_CLOCK") for k in sensors)


def test_available_sensors_units(backend):
    sensors = backend.availableSensors()
    assert sensors["CUDA:0_POWER"][2] == Unit.WATT
    assert sensors["CUDA:0_MEM"][2] == Unit.BYTE


def test_power_sensor_reads(backend):
    (sensor,) = backend.getSensors({"CUDA:0_POWER"})
    assert sensor.type == DeviceType.GPU
    assert sensor.dataType.unit == Unit.WATT
    assert int(sensor.read()) == 150000


def test_memory_sensor_reads_uint64(backend):
    (sensor,) = backend.getSensors({"CUDA:1_MEM"})
    value = sensor.read()
    assert value.dtype == np.uint64
    assert int(value) == 1024


def test_clock_sensor_reads(backend):
    clock_id = next(k for k in backend.availableSensors() if "CLOCK_SM" in k)
    (sensor,) = backend.getSensors({clock_id})
    assert sensor.type == DeviceType.GPU
    assert sensor.dataType.unit == Unit.HZ
    # Fake returns 1000 + clock index; SM clock id is 0.
    assert int(sensor.read()) == 1000


def test_power_callback_error_returns_zero(backend, fake_pynvml):
    (sensor,) = backend.getSensors({"CUDA:0_POWER"})

    def boom(handle):
        raise fake_pynvml.NVMLError("read failure")

    fake_pynvml.nvmlDeviceGetPowerUsage = boom
    assert int(sensor.read()) == 0


def test_mem_callback_error_returns_uint64_zero(backend, fake_pynvml):
    (sensor,) = backend.getSensors({"CUDA:0_MEM"})

    def boom(handle):
        raise fake_pynvml.NVMLError("read failure")

    fake_pynvml.nvmlDeviceGetMemoryInfo = boom
    value = sensor.read()
    assert int(value) == 0


def test_close_calls_shutdown(backend, fake_pynvml):
    backend.close()
    assert fake_pynvml._state["shutdown_calls"] >= 1
