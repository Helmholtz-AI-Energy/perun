import pandas as pd

from perun.data_model.data import MetricType
from perun.io.text_report import (
    DEFAULT_REGION_METRICS,
    DEFAULT_TABLE_METRICS,
    _parse_metric_list,
    _region_metric_label,
)
from perun.io.util import dataframe_to_markdown


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
