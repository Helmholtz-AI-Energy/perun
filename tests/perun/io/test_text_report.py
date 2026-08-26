import numpy as np
import pandas as pd
import pytest

from perun.data_model.data import DataNode, MetricType, NodeType, RawData
from perun.data_model.measurement_type import Magnitude, MetricMetaData, Unit
from perun.data_model.sensor import DeviceType
from perun.io.text_report import (
    DEFAULT_REGION_METRICS,
    DEFAULT_TABLE_METRICS,
    _parse_group_by,
    _parse_metric_list,
    _parse_stats_list,
    _region_metric_label,
    textReport,
)
from perun.io.util import dataframe_to_markdown, raw_metric_stats
from perun.processing import processSensorData


def _percent_md() -> MetricMetaData:
    return MetricMetaData(
        Unit.PERCENT,
        Magnitude.ONE,
        np.dtype("float32"),
        np.float32(0),
        np.float32(100),
        np.float32(-1),
    )


def _second_md() -> MetricMetaData:
    return MetricMetaData(
        Unit.SECOND,
        Magnitude.ONE,
        np.dtype("float32"),
        np.float32(0),
        np.float32(1000),
        np.float32(-1),
    )


def _make_cpu_util_sensor(sensor_id: str, values: list[float]) -> DataNode:
    raw = RawData(
        timesteps=np.arange(len(values), dtype=np.float32),
        values=np.array(values, dtype=np.float32),
        t_md=_second_md(),
        v_md=_percent_md(),
    )
    node = DataNode(
        id=sensor_id,
        type=NodeType.SENSOR,
        raw_data=raw,
        deviceType=DeviceType.CPU,
    )
    return processSensorData(node)


def test_parse_metric_list_defaults_on_empty():
    assert _parse_metric_list(None, DEFAULT_TABLE_METRICS) == DEFAULT_TABLE_METRICS
    assert _parse_metric_list("", DEFAULT_TABLE_METRICS) == DEFAULT_TABLE_METRICS
    assert _parse_metric_list("   ", DEFAULT_REGION_METRICS) == DEFAULT_REGION_METRICS


def test_parse_metric_list_parses_comma_and_space():
    assert _parse_metric_list("runtime,energy", DEFAULT_TABLE_METRICS) == [
        MetricType.RUNTIME,
        MetricType.ENERGY,
    ]
    assert _parse_metric_list("runtime energy", DEFAULT_TABLE_METRICS) == [
        MetricType.RUNTIME,
        MetricType.ENERGY,
    ]


def test_parse_metric_list_is_lenient_on_unknown(caplog):
    # An unknown metric is skipped (with a warning), known ones are kept.
    result = _parse_metric_list("runtime,not_a_metric,energy", DEFAULT_TABLE_METRICS)
    assert result == [MetricType.RUNTIME, MetricType.ENERGY]
    assert any("not_a_metric" in rec.message for rec in caplog.records)


def test_parse_metric_list_deduplicates():
    assert _parse_metric_list("runtime,runtime,energy", DEFAULT_TABLE_METRICS) == [
        MetricType.RUNTIME,
        MetricType.ENERGY,
    ]


def test_parse_metric_list_all_invalid_falls_back():
    assert _parse_metric_list("foo,bar", DEFAULT_TABLE_METRICS) == DEFAULT_TABLE_METRICS


def test_region_metric_label_known_and_unknown():
    assert _region_metric_label(MetricType.RUNTIME) == "Avg Runtime"
    # Unknown metrics get a generic label rather than raising a KeyError.
    assert _region_metric_label(MetricType.NET_READ) == "Avg NET_READ"


def test_dataframe_to_markdown_basic_shape():
    df = pd.DataFrame.from_records([{"A": 1, "B": "x"}, {"A": 22, "B": "yy"}])
    md = dataframe_to_markdown(df)
    lines = md.splitlines()
    assert lines[0] == "|  A |  B |"
    # Separator row: right-aligned columns end with a colon.
    assert set(lines[1]) <= set("|-:")
    assert lines[1].count("|") == 3
    assert len(lines) == 4  # header + separator + 2 rows


def test_dataframe_to_markdown_handles_missing_values():
    # Columns present in one record but not another produce NaN -> empty cell.
    df = pd.DataFrame.from_records([{"A": 1, "B": "x"}, {"A": 2}])
    md = dataframe_to_markdown(df)
    assert "nan" not in md.lower()


def test_parse_stats_list_defaults_and_aliases():
    assert _parse_stats_list(None) == ["avg"]
    assert _parse_stats_list("") == ["avg"]
    # Canonical avg, min, max ordering is always preserved.
    assert _parse_stats_list("max,min,avg") == ["avg", "min", "max"]
    # Aliases are accepted.
    assert _parse_stats_list("mean maximum minimum") == ["avg", "min", "max"]


def test_parse_stats_list_lenient_on_unknown(caplog):
    assert _parse_stats_list("avg,bogus,max") == ["avg", "max"]
    assert any("bogus" in rec.message for rec in caplog.records)
    # All invalid -> falls back to avg.
    assert _parse_stats_list("foo,bar") == ["avg"]


def test_parse_group_by():
    assert _parse_group_by(None) == "host"
    assert _parse_group_by("host") == "host"
    assert _parse_group_by("DEVICE") == "device"
    assert _parse_group_by("something-else") == "host"


def test_raw_metric_stats_from_sensor_series():
    # A device group with two CPU util sensors; min/max/avg must come from the
    # concatenated raw sample values.
    s1 = _make_cpu_util_sensor("CPU_UTIL_0", [10.0, 20.0, 30.0])
    s2 = _make_cpu_util_sensor("CPU_UTIL_1", [40.0, 50.0, 60.0])
    device_group = DataNode(
        id="cpu",
        type=NodeType.DEVICE_GROUP,
        nodes={s1.id: s1, s2.id: s2},
        deviceType=DeviceType.CPU,
    )

    result = raw_metric_stats(device_group, MetricType.CPU_UTIL)
    assert result is not None
    r_min, r_mean, r_max, _ = result
    assert float(r_min) == pytest.approx(10.0)
    assert float(r_max) == pytest.approx(60.0)
    assert float(r_mean) == pytest.approx(35.0)


def test_raw_metric_stats_returns_none_for_non_series_metric():
    s1 = _make_cpu_util_sensor("CPU_UTIL_0", [10.0, 20.0])
    device_group = DataNode(
        id="cpu",
        type=NodeType.DEVICE_GROUP,
        nodes={s1.id: s1},
        deviceType=DeviceType.CPU,
    )
    # RUNTIME has no per-sample series -> None.
    assert raw_metric_stats(device_group, MetricType.RUNTIME) is None


def _build_multirun_tree() -> DataNode:
    s1 = _make_cpu_util_sensor("CPU_UTIL_0", [10.0, 20.0, 30.0])
    s2 = _make_cpu_util_sensor("CPU_UTIL_1", [40.0, 50.0, 60.0])
    device_group = DataNode(
        id="cpu",
        type=NodeType.DEVICE_GROUP,
        nodes={s1.id: s1, s2.id: s2},
        deviceType=DeviceType.CPU,
        metrics={
            MetricType.CPU_UTIL: s1.metrics[MetricType.CPU_UTIL],
        },
    )
    host = DataNode(
        id="host0",
        type=NodeType.NODE,
        nodes={device_group.id: device_group},
        metrics={MetricType.CPU_UTIL: s1.metrics[MetricType.CPU_UTIL]},
    )
    run = DataNode(
        id="0",
        type=NodeType.RUN,
        nodes={host.id: host},
        metrics={MetricType.CPU_UTIL: s1.metrics[MetricType.CPU_UTIL]},
    )
    mr = DataNode(
        id="mr0",
        type=NodeType.MULTI_RUN,
        nodes={run.id: run},
        metadata={
            "benchmarking.metrics": "cpu_util",
            "benchmarking.group_by": "device",
            "benchmarking.metric_stats": "avg,min,max",
        },
        processed=True,
    )
    app = DataNode(
        id="app",
        type=NodeType.APP,
        nodes={mr.id: mr},
        metadata={
            "creation_dt": "2026-01-01T00:00:00",
            "last_execution_dt": "2026-01-01T00:00:00",
        },
        processed=True,
    )
    return app


def test_text_report_device_mode_includes_min_max_columns():
    app = _build_multirun_tree()
    report = textReport(app, "mr0")
    # Device breakdown adds a Device column and Min/Max headers for CPU_UTIL.
    assert "Device" in report
    assert "Min CPU_UTIL" in report
    assert "Max CPU_UTIL" in report
    # The per-device row should show min=10 and max=60 from the raw series.
    assert "10.00" in report or "10.000" in report
    assert "60.00" in report or "60.000" in report


def test_text_report_host_mode_has_no_device_column():
    app = _build_multirun_tree()
    app.nodes["mr0"].metadata["benchmarking.group_by"] = "host"
    app.nodes["mr0"].metadata["benchmarking.metric_stats"] = "avg"
    report = textReport(app, "mr0")
    assert "Device" not in report
    assert "Min CPU_UTIL" not in report
