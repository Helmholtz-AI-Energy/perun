import os
import tempfile
from unittest import mock

import pytest

from perun.configuration import (
    _default_config,
    config,
    read_custom_config,
    read_environ,
    sanitize_config,
    save_to_config,
)


# Helper function to reset the config to default before each test
def reset_config():
    config.clear()
    config.read_dict(_default_config)


@pytest.fixture(autouse=True)
def run_around_tests():
    reset_config()
    yield
    reset_config()


def test_read_custom_config():
    with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
        tmpfile.write(b"[post-processing]\npower_overhead = 10\n")
        tmpfile_path = tmpfile.name

    read_custom_config(tmpfile_path)
    assert config.getfloat("post-processing", "power_overhead") == 10

    os.remove(tmpfile_path)


def test_save_to_config():
    save_to_config("power_overhead", 20)
    assert config.getfloat("post-processing", "power_overhead") == 20


def test_read_environ():
    with mock.patch.dict(os.environ, {"PERUN_POWER_OVERHEAD": "30"}):
        read_environ()
        assert config.getfloat("post-processing", "power_overhead") == 30


def test_sanitize_config():
    config.set("post-processing", "power_overhead", "-10")
    config.set("post-processing", "pue", "0.5")
    config.set("post-processing", "emissions_factor", "-100")
    config.set("post-processing", "price_factor", "-1")
    config.set("monitor", "sampling_period", "0.05")
    config.set("monitor", "include_backends", "backend1")
    config.set("monitor", "exclude_backends", "backend2")
    config.set("monitor", "include_sensors", "sensor1")
    config.set("monitor", "exclude_sensors", "sensor2")
    config.set("output", "data_out", "./non_existent_dir")
    config.set("output", "format", "invalid_format")
    config.set("benchmarking", "rounds", "0")
    config.set("benchmarking", "warmup_rounds", "-1")
    config.set("debug", "log_lvl", "INVALID")

    sanitized_config = sanitize_config(config)

    assert sanitized_config.getfloat("post-processing", "power_overhead") == 0
    assert sanitized_config.getfloat("post-processing", "pue") == 1.0
    assert sanitized_config.getfloat("post-processing", "emissions_factor") == 417.80
    assert sanitized_config.getfloat("post-processing", "price_factor") == 0.3251
    assert sanitized_config.getfloat("monitor", "sampling_period") == 1
    assert sanitized_config.get("monitor", "include_backends") == ""
    assert sanitized_config.get("monitor", "include_sensors") == ""
    assert sanitized_config.get("output", "format") == "text"
    assert sanitized_config.getint("benchmarking", "rounds") == 1
    assert sanitized_config.getint("benchmarking", "warmup_rounds") == 0
    assert sanitized_config.get("debug", "log_lvl") == "WARNING"


def test_sanitize_config_valid_values():
    config.set("post-processing", "power_overhead", "10")
    config.set("post-processing", "pue", "1.5")
    config.set("post-processing", "emissions_factor", "500")
    config.set("post-processing", "price_factor", "0.5")
    config.set("monitor", "sampling_period", "2")
    config.set("output", "format", "json")
    config.set("benchmarking", "rounds", "5")
    config.set("benchmarking", "warmup_rounds", "2")
    config.set("debug", "log_lvl", "DEBUG")

    sanitized_config = sanitize_config(config)

    assert sanitized_config.getfloat("post-processing", "power_overhead") == 10
    assert sanitized_config.getfloat("post-processing", "pue") == 1.5
    assert sanitized_config.getfloat("post-processing", "emissions_factor") == 500
    assert sanitized_config.getfloat("post-processing", "price_factor") == 0.5
    assert sanitized_config.getfloat("monitor", "sampling_period") == 2
    assert sanitized_config.get("output", "format") == "json"
    assert sanitized_config.getint("benchmarking", "rounds") == 5
    assert sanitized_config.getint("benchmarking", "warmup_rounds") == 2
    assert sanitized_config.get("debug", "log_lvl") == "DEBUG"


def test_read_custom_config_invalid_path():
    invalid_path = "/invalid/path/to/config.ini"
    read_custom_config(invalid_path)
    # Ensure that the default config is still intact
    assert config.getfloat("post-processing", "power_overhead") == 0


def test_save_to_config_nonexistent_key():
    save_to_config("nonexistent_key", "value")
    # Ensure that the nonexistent key is not added to the config
    assert not config.has_option("post-processing", "nonexistent_key")


def test_read_environ_invalid_value():
    with mock.patch.dict(os.environ, {"PERUN_POWER_OVERHEAD": "invalid"}):
        read_environ()
        sanitize_config(config)
        # Ensure that the invalid value is not set
        assert config.getfloat("post-processing", "power_overhead") == 0


def test_sanitize_config_invalid_output_format():
    config.set("output", "format", "invalid_format")
    sanitized_config = sanitize_config(config)
    assert sanitized_config.get("output", "format") == "text"


def test_sanitize_config_invalid_log_level():
    config.set("debug", "log_lvl", "INVALID")
    sanitized_config = sanitize_config(config)
    assert sanitized_config.get("debug", "log_lvl") == "WARNING"
