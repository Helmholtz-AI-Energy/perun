from configparser import ConfigParser
from dataclasses import asdict

import numpy as np
import pytest

from perun.data_model.data import (
    DataNode,
    Metric,
    MetricType,
    NodeType,
    RawData,
    Stats,
)
from perun.data_model.measurement_type import Magnitude, MetricMetaData, Unit
from perun.data_model.sensor import DeviceType
from perun.processing import (
    getInterpolatedValues,
    processDataNode,
    processEnergyData,
    processSensorData,
)


def test_stats_fromdict_roundtrip_preserves_sum():
    # Regression: Stats.fromDict used to map "min" onto the "sum" field, losing
    # the real sum on any dict-based round-trip (json / pickle).
    from perun.data_model.data import AggregateType

    md = MetricMetaData(
        Unit.JOULE,
        Magnitude.ONE,
        np.dtype("float32"),
        np.float32(0),
        np.float32(1000),
        np.float32(-1),
    )
    stats = Stats.fromMetrics(
        [
            Metric(MetricType.ENERGY, np.float32(10.0), md, agg=AggregateType.SUM),
            Metric(MetricType.ENERGY, np.float32(20.0), md, agg=AggregateType.SUM),
            Metric(MetricType.ENERGY, np.float32(30.0), md, agg=AggregateType.SUM),
        ]
    )
    assert float(stats.sum) == pytest.approx(60.0)
    assert float(stats.min) == pytest.approx(10.0)
    assert float(stats.max) == pytest.approx(30.0)

    restored = Stats.fromDict(asdict(stats))
    assert float(restored.sum) == pytest.approx(float(stats.sum))
    assert float(restored.mean) == pytest.approx(float(stats.mean))
    assert float(restored.std) == pytest.approx(float(stats.std))
    assert float(restored.min) == pytest.approx(float(stats.min))
    assert float(restored.max) == pytest.approx(float(stats.max))
    # The bug conflated sum and min; make sure they are now distinct.
    assert float(restored.sum) != float(restored.min)


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


def _energy_sensor(node_id: str) -> DataNode:
    """Build a processed-able energy sensor node yielding 40 J / 10 W."""
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
    return DataNode(
        id=node_id,
        type=NodeType.SENSOR,
        raw_data=raw_data,
        deviceType=DeviceType.CPU,
    )


def _post_processing_config() -> ConfigParser:
    config = ConfigParser()
    config.add_section("post-processing")
    config.set("post-processing", "power_overhead", "0.0")
    config.set("post-processing", "pue", "1.0")
    config.set("post-processing", "emissions_factor", "0.5")
    config.set("post-processing", "price_factor", "0.1")
    return config


@pytest.mark.parametrize(
    "deviceType", [DeviceType.SYSIO, DeviceType.SOCKET, DeviceType.OTHER]
)
def test_processDataNode_skips_socket_level_device_types(deviceType):
    # Group nodes describing socket-level power (SYSIO/SOCKET/OTHER) must not
    # have their child metrics aggregated up, to avoid double counting them
    # against node totals that already include CPU/RAM sensors.
    group = DataNode(
        id="group_node",
        type=NodeType.DEVICE_GROUP,
        nodes={"sensor": _energy_sensor("sensor_node")},
        deviceType=deviceType,
    )
    processed = processDataNode(group, _post_processing_config(), force_process=True)
    assert MetricType.ENERGY not in processed.metrics
    assert MetricType.POWER not in processed.metrics
    # The child sensor itself is still processed.
    assert MetricType.ENERGY in processed.nodes["sensor"].metrics


def test_processDataNode_aggregates_regular_device_types():
    # Sanity check contrast: a CPU device group DOES aggregate its children.
    group = DataNode(
        id="group_node",
        type=NodeType.DEVICE_GROUP,
        nodes={"sensor": _energy_sensor("sensor_node")},
        deviceType=DeviceType.CPU,
    )
    processed = processDataNode(group, _post_processing_config(), force_process=True)
    assert processed.metrics[MetricType.ENERGY].value == pytest.approx(40.0)
    assert processed.metrics[MetricType.POWER].value == pytest.approx(10.0)


def test_getInterpolatedValues():
    t = np.array([0, 1, 2, 3, 4], dtype=np.float32)
    x = np.array([0, 10, 20, 30, 40], dtype=np.float32)
    start, end = np.float32(1), np.float32(3.5)
    new_t, new_x = getInterpolatedValues(t, x, start, end)
    assert np.array_equal(new_t, np.array([1, 1, 2, 3, 3.5], dtype=np.float32))
    assert np.array_equal(new_x, np.array([10, 10, 20, 30, 35], dtype=np.float32))
