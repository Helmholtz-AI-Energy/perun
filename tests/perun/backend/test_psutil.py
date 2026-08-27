"""Unit tests for the psutil backend.

``psutil`` is a hard dependency of perun and is always importable, so these
tests exercise the real backend and only patch the individual ``psutil``
functions where a deterministic reading is required.
"""

import numpy as np
import pytest

from perun.backend.psutil import PSUTILBackend
from perun.data_model.measurement_type import Unit
from perun.data_model.sensor import DeviceType


@pytest.fixture()
def backend(setup_cleanup):
    """Return a fresh PSUTILBackend instance (singletons reset by fixture)."""
    return PSUTILBackend()


def test_metadata_contains_source(backend):
    assert "source" in backend.metadata
    assert backend.metadata["source"].startswith("psutil")


def test_available_sensors_shape(backend):
    sensors = backend.availableSensors()
    assert isinstance(sensors, dict)
    assert len(sensors) > 0
    for sensor_id, meta in sensors.items():
        # (backend_id, DeviceType, Unit)
        assert meta[0] == backend.id
        assert isinstance(meta[1], DeviceType)
        assert isinstance(meta[2], Unit)


def test_ram_and_cpu_sensors_present(backend):
    sensors = backend.availableSensors()
    assert "RAM_USAGE" in sensors
    assert any(s.startswith("CPU_USAGE_") for s in sensors)


def test_get_sensors_returns_requested(backend):
    available = set(backend.availableSensors().keys())
    requested = {s for s in available if s == "RAM_USAGE" or s.startswith("CPU_USAGE_")}
    sensors = backend.getSensors(requested)
    returned_ids = {s.id for s in sensors}
    assert returned_ids == requested


def test_ram_sensor_reads_uint64(backend):
    (sensor,) = backend.getSensors({"RAM_USAGE"})
    assert sensor.type == DeviceType.RAM
    assert sensor.dataType.unit == Unit.BYTE
    value = sensor.read()
    assert np.issubdtype(np.asarray(value).dtype, np.integer)
    assert value >= 0


def test_cpu_usage_sensor_reads_percent(backend):
    cpu_ids = [s for s in backend.availableSensors() if s.startswith("CPU_USAGE_")]
    (sensor,) = backend.getSensors({cpu_ids[0]})
    assert sensor.type == DeviceType.CPU
    assert sensor.dataType.unit == Unit.PERCENT
    value = float(sensor.read())
    assert 0.0 <= value <= 100.0


def test_get_callback_invalid_device_raises(backend):
    with pytest.raises(ValueError):
        backend._getCallback("NOT_A_REAL_DEVICE")


def test_close_is_noop(backend):
    # Should not raise.
    backend.close()
