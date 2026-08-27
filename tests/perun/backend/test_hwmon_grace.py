"""Unit tests for the hwmon (Grace) backend.

The backend reads power counters from the Linux hwmon sysfs hierarchy
(``/sys/class/hwmon``). Each hwmon device may expose ``power<N>_average``
sensors (in microwatts) inside its ``device`` subdirectory, together with a
``power<N>_oem_info`` file describing the socket the sensor belongs to.

To keep the tests hardware independent we build a fake sysfs tree under
``tmp_path`` and point the backend at it via the module-level ``HWMON_PATH``.
``cpuinfo.get_cpu_info`` is monkeypatched so the tests do not depend on the
machine they run on.
"""

import numpy as np
import pytest

import perun.backend.hwmon_grace as hwmon_mod
from perun.backend.hwmon_grace import HWMonGraceBackend
from perun.data_model.measurement_type import Magnitude, Unit
from perun.data_model.sensor import DeviceType


def _write(path, content):
    path.write_text(str(content))


def _make_hwmon_device(root, index, sensors):
    """Create an ``hwmon<index>`` device with power sensors.

    Parameters
    ----------
    root:
        The fake ``/sys/class/hwmon`` root directory.
    index:
        Numeric index of the hwmon device (``hwmon0``, ``hwmon1``, ...).
    sensors:
        Iterable of ``(sensor_index, oem_info, power_uw)`` tuples. For each
        entry a ``power<sensor_index>_average`` and matching
        ``power<sensor_index>_oem_info`` file is created.
    """
    hwmon = root / f"hwmon{index}"
    device = hwmon / "device"
    device.mkdir(parents=True)
    for sensor_index, oem_info, power_uw in sensors:
        _write(device / f"power{sensor_index}_average", power_uw)
        _write(device / f"power{sensor_index}_oem_info", oem_info)
    return hwmon


@pytest.fixture()
def fake_hwmon(tmp_path, monkeypatch, setup_cleanup):
    """Create a fake hwmon tree that mimics an NVIDIA Grace node."""
    hwmon_root = tmp_path / "hwmon"
    hwmon_root.mkdir()
    _make_hwmon_device(
        hwmon_root,
        0,
        [
            (1, "Grace Power Socket 0", 55_000_000),
            (2, "CPU Power Socket 0", 40_000_000),
            (3, "SysIO Power Socket 0", 10_000_000),
        ],
    )
    _make_hwmon_device(
        hwmon_root,
        1,
        [
            (1, "Module Power Socket 0", 90_000_000),
        ],
    )
    monkeypatch.setattr(hwmon_mod, "HWMON_PATH", str(hwmon_root))
    # cpuinfo probes the real host; stub it out so tests are deterministic.
    monkeypatch.setattr(
        hwmon_mod.cpuinfo, "get_cpu_info", lambda: {"brand_raw": "NVIDIA Grace"}
    )
    return hwmon_root


@pytest.fixture()
def backend(fake_hwmon):
    b = HWMonGraceBackend()
    yield b
    b.close()


def test_setup_discovers_all_power_sensors(backend):
    sensors = backend.availableSensors()
    # 3 sensors on hwmon0 + 1 sensor on hwmon1 = 4 devices.
    assert len(sensors) == 4


# Sensor ids are the OEM label, qualified with the hwmon device name and the
# power sensor index so they are unique even for duplicate/empty labels.
GRACE_ID = "grace_power_socket_0_hwmon0_power1"
CPU_ID = "cpu_power_socket_0_hwmon0_power2"
SYSIO_ID = "sysio_power_socket_0_hwmon0_power3"
MODULE_ID = "module_power_socket_0_hwmon1_power1"


def test_sensor_ids_derived_from_oem_info(backend):
    ids = set(backend.availableSensors().keys())
    assert GRACE_ID in ids
    assert CPU_ID in ids
    assert SYSIO_ID in ids
    assert MODULE_ID in ids


def test_device_types_mapped_from_oem_info(backend):
    sensors = backend.availableSensors()
    assert sensors[GRACE_ID][1] == DeviceType.SOCKET
    assert sensors[CPU_ID][1] == DeviceType.CPU
    assert sensors[SYSIO_ID][1] == DeviceType.SYSIO
    # "Module Power Socket" is intentionally mapped to OTHER by the backend.
    assert sensors[MODULE_ID][1] == DeviceType.OTHER


def test_available_sensors_units_are_watt(backend):
    for _, (backend_id, _dev_type, unit) in backend.availableSensors().items():
        assert backend_id == backend.id
        assert unit == Unit.WATT


def test_sensor_metadata_and_magnitude(backend):
    (sensor,) = backend.getSensors({GRACE_ID})
    assert sensor.dataType.unit == Unit.WATT
    # power*_average is reported in microwatts.
    assert sensor.dataType.mag == Magnitude.MICRO
    assert sensor.metadata["sensor_type"] == "power_average"
    assert sensor.metadata["device_name"] == "Grace Power Socket 0"
    assert sensor.metadata["hwmon_device"] == "hwmon0"


def test_get_sensors_and_read(backend):
    ids = set(backend.availableSensors().keys())
    sensors = backend.getSensors(ids)
    assert {s.id for s in sensors} == ids
    for sensor in sensors:
        value = sensor.read()
        assert np.issubdtype(np.asarray(value).dtype, np.integer)
        assert value >= 0


def test_read_returns_file_value(backend):
    (sensor,) = backend.getSensors({CPU_ID})
    assert int(sensor.read()) == 40_000_000


def test_callback_reads_current_file_value(backend, fake_hwmon):
    (sensor,) = backend.getSensors({GRACE_ID})
    first = int(sensor.read())

    # The backend keeps the file handle open and seeks to 0, so we must update
    # the file in place (truncating the same inode) rather than replacing it.
    power_file = fake_hwmon / "hwmon0" / "device" / "power1_average"
    with open(power_file, "r+") as fh:
        fh.seek(0)
        fh.truncate()
        fh.write(str(first + 12345))
    second = int(sensor.read())
    assert second == first + 12345


def test_read_empty_file_returns_zero(backend, fake_hwmon):
    (sensor,) = backend.getSensors({CPU_ID})
    power_file = fake_hwmon / "hwmon0" / "device" / "power2_average"
    with open(power_file, "r+") as fh:
        fh.seek(0)
        fh.truncate()
    assert int(sensor.read()) == 0


def test_missing_hwmon_raises_import_warning(tmp_path, monkeypatch, setup_cleanup):
    monkeypatch.setattr(hwmon_mod, "HWMON_PATH", str(tmp_path / "does_not_exist"))
    monkeypatch.setattr(
        hwmon_mod.cpuinfo, "get_cpu_info", lambda: {"brand_raw": "NVIDIA Grace"}
    )
    with pytest.raises(ImportWarning):
        HWMonGraceBackend()


def test_no_power_sensors_yields_empty_backend(tmp_path, monkeypatch, setup_cleanup):
    """An hwmon device without power*_average files produces no sensors."""
    hwmon_root = tmp_path / "hwmon"
    device = hwmon_root / "hwmon0" / "device"
    device.mkdir(parents=True)
    # Only unrelated sensor files present.
    _write(device / "temp1_input", 45000)
    monkeypatch.setattr(hwmon_mod, "HWMON_PATH", str(hwmon_root))
    monkeypatch.setattr(
        hwmon_mod.cpuinfo, "get_cpu_info", lambda: {"brand_raw": "NVIDIA Grace"}
    )
    b = HWMonGraceBackend()
    assert b.availableSensors() == {}
    b.close()


def test_duplicate_oem_labels_do_not_collide(tmp_path, monkeypatch, setup_cleanup):
    """Two sensors sharing an OEM label must produce distinct sensor ids."""
    hwmon_root = tmp_path / "hwmon"
    hwmon_root.mkdir()
    # Same OEM label on two different hwmon devices.
    _make_hwmon_device(hwmon_root, 0, [(1, "Grace Power Socket 0", 10_000_000)])
    _make_hwmon_device(hwmon_root, 1, [(1, "Grace Power Socket 0", 20_000_000)])
    monkeypatch.setattr(hwmon_mod, "HWMON_PATH", str(hwmon_root))
    monkeypatch.setattr(
        hwmon_mod.cpuinfo, "get_cpu_info", lambda: {"brand_raw": "NVIDIA Grace"}
    )
    b = HWMonGraceBackend()
    ids = set(b.availableSensors().keys())
    # Both sensors are retained (no silent overwrite).
    assert len(ids) == 2
    assert "grace_power_socket_0_hwmon0_power1" in ids
    assert "grace_power_socket_0_hwmon1_power1" in ids
    b.close()


def test_empty_oem_info_falls_back_to_device_and_index(
    tmp_path, monkeypatch, setup_cleanup
):
    """A power sensor without an OEM label still gets a deterministic id."""
    hwmon_root = tmp_path / "hwmon"
    device = hwmon_root / "hwmon0" / "device"
    device.mkdir(parents=True)
    _write(device / "power1_average", 5_000_000)
    # No power1_oem_info file at all -> empty label.
    monkeypatch.setattr(hwmon_mod, "HWMON_PATH", str(hwmon_root))
    monkeypatch.setattr(
        hwmon_mod.cpuinfo, "get_cpu_info", lambda: {"brand_raw": "NVIDIA Grace"}
    )
    b = HWMonGraceBackend()
    ids = set(b.availableSensors().keys())
    assert ids == {"hwmon0_power1"}
    b.close()


def test_missing_device_subdir_is_skipped(tmp_path, monkeypatch, setup_cleanup):
    """hwmon entries without a ``device`` subdirectory are ignored."""
    hwmon_root = tmp_path / "hwmon"
    (hwmon_root / "hwmon0").mkdir(parents=True)  # no "device" subdirectory
    monkeypatch.setattr(hwmon_mod, "HWMON_PATH", str(hwmon_root))
    monkeypatch.setattr(
        hwmon_mod.cpuinfo, "get_cpu_info", lambda: {"brand_raw": "NVIDIA Grace"}
    )
    b = HWMonGraceBackend()
    assert b.availableSensors() == {}
    b.close()


def test_close_closes_files(backend):
    backend.close()
    for f in backend._files:
        assert f.closed
