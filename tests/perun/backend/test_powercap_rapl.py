"""Unit tests for the Powercap RAPL backend.

The backend reads energy counters from the Linux powercap sysfs hierarchy
(``/sys/class/powercap``). To keep the tests hardware independent we build a
fake sysfs tree under ``tmp_path`` and point the backend at it via the
module-level ``RAPL_PATH``.
"""

import numpy as np
import pytest

import perun.backend.powercap_rapl as rapl_mod
from perun.backend.powercap_rapl import PowercapRAPLBackend
from perun.data_model.measurement_type import Unit
from perun.data_model.sensor import DeviceType


def _write(path, content):
    path.write_text(str(content))


def _make_package(root, socket, package_energy=1000, dram_energy=500):
    """Create an ``intel-rapl:<socket>`` package with a nested dram subdomain."""
    pkg = root / f"intel-rapl:{socket}"
    pkg.mkdir()
    _write(pkg / "name", f"package-{socket}")
    _write(pkg / "energy_uj", package_energy)
    _write(pkg / "max_energy_range_uj", 262143328850)

    dram = pkg / f"intel-rapl:{socket}:0"
    dram.mkdir()
    _write(dram / "name", "dram")
    _write(dram / "energy_uj", dram_energy)
    _write(dram / "max_energy_range_uj", 65712999613)
    return pkg


@pytest.fixture()
def fake_rapl(tmp_path, monkeypatch, setup_cleanup):
    """Create a fake powercap tree and point the backend at it."""
    powercap = tmp_path / "powercap"
    powercap.mkdir()
    _make_package(powercap, 0)
    _make_package(powercap, 1)
    monkeypatch.setattr(rapl_mod, "RAPL_PATH", str(powercap))
    return powercap


@pytest.fixture()
def backend(fake_rapl):
    b = PowercapRAPLBackend()
    yield b
    b.close()


def test_setup_discovers_package_and_dram(backend):
    sensors = backend.availableSensors()
    # 2 sockets x (package + dram) = 4 devices.
    assert len(sensors) == 4
    types = {meta[1] for meta in sensors.values()}
    assert DeviceType.CPU in types
    assert DeviceType.RAM in types


def test_available_sensors_units_are_joule(backend):
    for _, (backend_id, _dev_type, unit) in backend.availableSensors().items():
        assert backend_id == backend.id
        assert unit == Unit.JOULE


def test_get_sensors_and_read(backend):
    ids = set(backend.availableSensors().keys())
    sensors = backend.getSensors(ids)
    assert {s.id for s in sensors} == ids
    for sensor in sensors:
        value = sensor.read()
        assert np.issubdtype(np.asarray(value).dtype, np.integer)
        assert value >= 0


def test_callback_reads_current_file_value(backend, fake_rapl):
    ids = list(backend.availableSensors().keys())
    # Sensor ids have the form "cpu_<socket>_package-<socket>"; pick a package
    # sensor and derive its backing energy file from the socket number so the
    # test targets the exact file that sensor reads from.
    package_id = next(i for i in ids if i.startswith("cpu_"))
    socket = package_id.split("_")[1]
    (sensor,) = backend.getSensors({package_id})

    first = int(sensor.read())
    # Simulate the counter advancing on disk and confirm the callback re-reads.
    # The backend keeps the file handle open and seeks to 0, so we must update
    # the file in place (truncating the same inode) rather than replacing it.
    pkg_energy_file = fake_rapl / f"intel-rapl:{socket}" / "energy_uj"
    with open(pkg_energy_file, "r+") as fh:
        fh.seek(0)
        fh.truncate()
        fh.write(str(first + 12345))
    second = int(sensor.read())
    assert second == first + 12345


def test_missing_powercap_raises_import_warning(tmp_path, monkeypatch, setup_cleanup):
    monkeypatch.setattr(rapl_mod, "RAPL_PATH", str(tmp_path / "does_not_exist"))
    with pytest.raises(ImportWarning):
        PowercapRAPLBackend()


def test_close_closes_files(backend):
    backend.close()
    for f in backend._files:
        assert f.closed
