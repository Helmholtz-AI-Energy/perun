# noqa
import random
from unittest.mock import Mock

import numpy as np
import pytest

from perun.data_model.measurement_type import Magnitude, MetricMetaData, Unit

# import perun.backend
from perun.data_model.sensor import DeviceType


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
    cpu.type = DeviceType.CPU
    cpu.metadata = {"long_name": "long_cpu"}
    cpu.dataType = MetricMetaData(
        Unit.JOULE,
        Magnitude.ONE,
        np.dtype("int32"),
        np.int32(0),
        np.int32(1000),
        np.int32(-1),
    )
    cpu.measureCallback = fake_energy
    cpu.read.return_value = lambda: fake_energy()
    cpu.toDict.return_value = {
        "id": cpu.id,
        "type": cpu.type,
        "metadata": cpu.metadata,
        "dataType": cpu.dataType,
    }
    return cpu


@pytest.fixture
def gpu():
    gpu = Mock()
    gpu.id = "FPU"
    gpu.type = DeviceType.CPU
    gpu.metadata = {"long_name": "long_gpu"}
    gpu.dataType = MetricMetaData(
        Unit.WATT,
        Magnitude.MICRO,
        np.dtype("float32"),
        np.float32(0.0),
        np.float32(1.0),
        np.float32(-1),
    )
    gpu.measureCallback = fake_power
    gpu.read.return_value = lambda: fake_power()
    gpu.toDict.return_value = {
        "id": gpu.id,
        "type": gpu.type,
        "metadata": gpu.metadata,
        "dataType": gpu.dataType,
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


# @pytest.fixture(autouse=True)
# def backends(monkeypatch: pytest.MonkeyPatch, cpu_backend, gpu_backend):
#     backends = [cpu_backend, gpu_backend]
#     monkeypatch.setattr(perun.backend, "backends", backends)
#     return backends
