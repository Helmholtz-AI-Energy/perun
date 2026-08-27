"""Tests for the perun monitoring subprocess helpers."""

import logging

from perun.monitoring.subprocess import _warnOnSlowRead


def test_warn_on_slow_read_emits_warning(caplog):
    # A read slower than the sampling period should trigger a warning that
    # points the user towards sensor/backend filtering.
    with caplog.at_level(logging.WARNING, logger="perun.monitoring.subprocess"):
        warned = _warnOnSlowRead(delta=2.0, sampling_period=1.0, warned=False)

    assert warned is True
    assert len(caplog.records) == 1
    message = caplog.records[0].getMessage()
    assert "longer than the sampling" in message
    assert "exclude_sensors" in message
    assert "--exclude-sensors" in message


def test_warn_on_slow_read_no_warning_when_fast(caplog):
    # A read faster than the sampling period should not warn.
    with caplog.at_level(logging.WARNING, logger="perun.monitoring.subprocess"):
        warned = _warnOnSlowRead(delta=0.1, sampling_period=1.0, warned=False)

    assert warned is False
    assert len(caplog.records) == 0


def test_warn_on_slow_read_only_warns_once(caplog):
    # Once warned, subsequent slow reads must not repeat the warning.
    with caplog.at_level(logging.WARNING, logger="perun.monitoring.subprocess"):
        warned = _warnOnSlowRead(delta=2.0, sampling_period=1.0, warned=True)

    assert warned is True
    assert len(caplog.records) == 0
