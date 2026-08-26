"""Unit tests for the ROCM (AMD) backend using a fake ``amdsmi`` module.

The backend imports ``amdsmi`` lazily via ``importlib.import_module``. We inject
a fake module into ``sys.modules`` so the backend can be exercised without an
AMD GPU or the real bindings installed.
"""

import enum
import sys
import types

import numpy as np
import pytest

from perun.data_model.measurement_type import Unit
from perun.data_model.sensor import DeviceType


class _AmdSmiException(Exception):
    pass


class _AmdSmiMemoryType(enum.Enum):
    VRAM = "vram"


class _AmdSmiInitFlags(enum.Enum):
    INIT_AMD_GPUS = 1


def _make_fake_amdsmi(n_devices=2, power=120, mem_used=2048, mem_total=16384):
    mod = types.ModuleType("amdsmi")
    mod.AmdSmiException = _AmdSmiException
    mod.AmdSmiMemoryType = _AmdSmiMemoryType
    mod.AmdSmiInitFlags = _AmdSmiInitFlags

    state = {"init_calls": 0, "shutdown_calls": 0}
    mod._state = state

    handles = [{"index": i} for i in range(n_devices)]

    def amdsmi_init(flags):
        state["init_calls"] += 1

    def amdsmi_shut_down():
        state["shutdown_calls"] += 1

    def amdsmi_get_lib_version():
        return {"major": 6, "minor": 2, "patch": 0}

    def amdsmi_get_processor_handles():
        return handles

    def amdsmi_get_gpu_device_uuid(handle):
        return f"amd-uuid-{handle['index']}"

    def amdsmi_get_power_info(handle):
        return {"average_socket_power": power, "power_limit": 300 * 10**6}

    def amdsmi_get_gpu_board_info(handle):
        return {"product_name": f"FakeAMD{handle['index']}"}

    def amdsmi_get_gpu_memory_usage(handle, mem_type):
        return mem_used

    def amdsmi_get_gpu_memory_total(handle, mem_type):
        return mem_total

    mod.amdsmi_init = amdsmi_init
    mod.amdsmi_shut_down = amdsmi_shut_down
    mod.amdsmi_get_lib_version = amdsmi_get_lib_version
    mod.amdsmi_get_processor_handles = amdsmi_get_processor_handles
    mod.amdsmi_get_gpu_device_uuid = amdsmi_get_gpu_device_uuid
    mod.amdsmi_get_power_info = amdsmi_get_power_info
    mod.amdsmi_get_gpu_board_info = amdsmi_get_gpu_board_info
    mod.amdsmi_get_gpu_memory_usage = amdsmi_get_gpu_memory_usage
    mod.amdsmi_get_gpu_memory_total = amdsmi_get_gpu_memory_total
    return mod


@pytest.fixture()
def fake_amdsmi(monkeypatch, setup_cleanup):
    mod = _make_fake_amdsmi()
    monkeypatch.setitem(sys.modules, "amdsmi", mod)
    return mod


@pytest.fixture()
def backend(fake_amdsmi):
    from perun.backend.rocmsmi import ROCMBackend

    b = ROCMBackend()
    yield b
    b.close()


def test_setup_metadata(backend):
    md = backend.metadata
    assert md["n_devices"] == 2
    assert "amdsmi_version" in md


def test_available_sensors_power_and_mem(backend):
    sensors = backend.availableSensors()
    # 2 devices * (power + mem) = 4 sensors.
    assert len(sensors) == 4
    assert any(s.endswith("_POWER") for s in sensors)
    assert any(s.endswith("_MEM") for s in sensors)


def test_available_sensors_units(backend):
    sensors = backend.availableSensors()
    for sensor_id, (_backend_id, dev_type, unit) in sensors.items():
        assert dev_type == DeviceType.GPU
        if sensor_id.endswith("_POWER"):
            assert unit == Unit.WATT
        elif sensor_id.endswith("_MEM"):
            assert unit == Unit.BYTE


def test_power_sensor_reads(backend):
    power_id = next(s for s in backend.availableSensors() if s.endswith("_POWER"))
    (sensor,) = backend.getSensors({power_id})
    assert sensor.dataType.unit == Unit.WATT
    assert int(sensor.read()) == 120


def test_mem_sensor_reads_uint64(backend):
    mem_id = next(s for s in backend.availableSensors() if s.endswith("_MEM"))
    (sensor,) = backend.getSensors({mem_id})
    value = sensor.read()
    assert value.dtype == np.uint64
    assert int(value) == 2048


def test_power_callback_error_returns_zero(backend, fake_amdsmi):
    power_id = next(s for s in backend.availableSensors() if s.endswith("_POWER"))
    (sensor,) = backend.getSensors({power_id})

    def boom(handle):
        raise fake_amdsmi.AmdSmiException("read failure")

    fake_amdsmi.amdsmi_get_power_info = boom
    assert int(sensor.read()) == 0


def test_close_calls_shutdown(backend, fake_amdsmi):
    backend.close()
    assert fake_amdsmi._state["shutdown_calls"] >= 1
