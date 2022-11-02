import random
from unittest.mock import Mock

import pytest

import perun.backend
from perun.units import Joule, Watt


def fake_energy():
    x = 0
    while True:
        x = (x + random.randint(1, 20)) % 1000
        yield x


def fake_power():
    return random.randint(0, 1000)


@pytest.fixture
def cpu():
    cpu = Mock()
    cpu.id = "FPU"
    cpu.long_name = "Fake CPU"
    cpu.unit = Joule()
    cpu.mag = ""
    cpu.min = 0
    cpu.max = 1000
    cpu.dtype = "uint32"
    cpu.measureCallback = fake_energy
    cpu.read.return_value = lambda: fake_energy()
    cpu.toDict.return_value = {
        "id": cpu.id,
        "long_name": cpu.long_name,
        "unit": cpu.unit,
        "mag": cpu.mag,
        "min": cpu.max,
        "max": cpu.dtype,
    }
    return cpu


@pytest.fixture
def gpu():
    gpu = Mock()
    gpu.id = "FGPU"
    gpu.long_name = "Fake GPU"
    gpu.unit = Watt()
    gpu.mag = ""
    gpu.min = 0
    gpu.max = 1000
    gpu.dtype = "uint32"
    gpu.measureCallback = fake_power
    gpu.read.return_value = lambda: fake_power()
    gpu.toDict.return_value = {
        "id": gpu.id,
        "long_name": gpu.long_name,
        "unit": gpu.unit,
        "mag": gpu.mag,
        "min": gpu.max,
        "max": gpu.dtype,
    }
    return gpu


@pytest.fixture
def cpu_backend(cpu):
    cpuBackend = Mock()
    cpuBackend.name = "Fake cpu backend"
    cpuBackend.visibleDevices.return_value = cpu.id
    cpuBackend.getDevices.side_effect = lambda id: {cpu} if id == cpu.id else set()
    return cpuBackend


@pytest.fixture
def gpu_backend(gpu):
    gpuBackend = Mock()
    gpuBackend.name = "Fake gpu backend"
    gpuBackend.visibleDevices.return_value = gpu.id
    gpuBackend.getDevices.side_effect = lambda id: {gpu} if id == gpu.id else set()
    return gpuBackend


@pytest.fixture(autouse=True)
def backends(monkeypatch: pytest.MonkeyPatch, cpu_backend, gpu_backend):
    backends = [cpu_backend, gpu_backend]
    monkeypatch.setattr(perun.backend, "backends", backends)
    return backends
