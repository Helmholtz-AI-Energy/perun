from configparser import ConfigParser

import numpy as np
import pytest

from perun.data_model.data import (
    DataNode,
    MetricType,
    NodeType,
    RawData,
)
from perun.data_model.measurement_type import Magnitude, MetricMetaData, Unit
from perun.data_model.sensor import DeviceType
from perun.processing import (
    getInterpolatedValues,
    processDataNode,
    processEnergyData,
    processSensorData,
)


def test_processEnergyData():
    raw_data = RawData(
        timesteps=np.array([0, 1, 2, 3, 4], dtype=np.float32),
        values=np.array([0, 10, 20, 30, 40], dtype=np.float32),
        t_md=MetricMetaData(
            Unit.SECOND,
            Magnitude.ONE,
            np.dtype("float32"),
            np.int32(0),
            np.int32(100),
            np.int32(-1),
        ),
        v_md=MetricMetaData(
            Unit.JOULE,
            Magnitude.ONE,
            np.dtype("float32"),
            np.int32(0),
            np.int32(100),
            np.int32(-1),
        ),
    )
    energy, power = processEnergyData(raw_data)
    assert energy == pytest.approx(40.0)
    assert power == pytest.approx(10.0)


def test_processSensorData():
    raw_data = RawData(
        timesteps=np.array([0, 1, 2, 3, 4], dtype=np.float32),
        values=np.array([0, 10, 20, 30, 40], dtype=np.float32),
        t_md=MetricMetaData(
            Unit.SECOND,
            Magnitude.ONE,
            np.dtype("float32"),
            np.int32(0),
            np.int32(100),
            np.int32(-1),
        ),
        v_md=MetricMetaData(
            Unit.JOULE,
            Magnitude.ONE,
            np.dtype("float32"),
            np.int32(0),
            np.int32(100),
            np.int32(-1),
        ),
    )
    sensor_data = DataNode(
        id="test_node",
        type=NodeType.SENSOR,
        raw_data=raw_data,
        deviceType=DeviceType.CPU,
    )
    processed_data = processSensorData(sensor_data)
    assert MetricType.ENERGY in processed_data.metrics
    assert MetricType.POWER in processed_data.metrics
    assert sensor_data.metrics[MetricType.ENERGY].value == pytest.approx(40.0)
    assert sensor_data.metrics[MetricType.POWER].value == pytest.approx(10.0)


def test_processDataNode():
    raw_data = RawData(
        timesteps=np.array([0, 1, 2, 3, 4], dtype=np.float32),
        values=np.array([0, 10, 20, 30, 40], dtype=np.float32),
        t_md=MetricMetaData(
            Unit.SECOND,
            Magnitude.ONE,
            np.dtype("float32"),
            np.int32(0),
            np.int32(100),
            np.int32(-1),
        ),
        v_md=MetricMetaData(
            Unit.JOULE,
            Magnitude.ONE,
            np.dtype("float32"),
            np.int32(0),
            np.int32(100),
            np.int32(-1),
        ),
    )
    sensor_data = DataNode(
        id="sensor_node",
        type=NodeType.SENSOR,
        raw_data=raw_data,
        deviceType=DeviceType.CPU,
    )
    devcie_data = DataNode(
        id="app_node", type=NodeType.DEVICE_GROUP, nodes={"sensor": sensor_data}
    )
    config = ConfigParser()
    config.add_section("post-processing")
    config.set("post-processing", "power_overhead", "10.0")
    config.set("post-processing", "pue", "1.5")
    config.set("post-processing", "emissions_factor", "0.5")
    config.set("post-processing", "price_factor", "0.1")
    processed_data = processDataNode(devcie_data, config, force_process=True)
    print(processed_data.metrics)
    assert MetricType.ENERGY in processed_data.metrics
    assert MetricType.POWER in processed_data.metrics
    assert processed_data.metrics[MetricType.ENERGY].value == pytest.approx(40.0)
    assert processed_data.metrics[MetricType.POWER].value == pytest.approx(10.0)


def test_getInterpolatedValues():
    t = np.array([0, 1, 2, 3, 4], dtype=np.float32)
    x = np.array([0, 10, 20, 30, 40], dtype=np.float32)
    start, end = np.float32(1), np.float32(3.5)
    new_t, new_x = getInterpolatedValues(t, x, start, end)
    assert np.array_equal(new_t, np.array([1, 1, 2, 3, 3.5], dtype=np.float32))
    assert np.array_equal(new_x, np.array([10, 10, 20, 30, 35], dtype=np.float32))
