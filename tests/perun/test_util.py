from perun.util import filter_sensors, increaseIdCounter


def test_increaseIdCounter_no_existing_ids():
    existing = []
    newId = "test"
    result = increaseIdCounter(existing, newId)
    assert result == "test"


def test_increaseIdCounter_existing_ids_no_match():
    existing = ["test_1", "test_2"]
    newId = "new_test"
    result = increaseIdCounter(existing, newId)
    assert result == "new_test"


def test_increaseIdCounter_existing_ids_match():
    existing = ["test", "test_1", "test_2"]
    newId = "test"
    result = increaseIdCounter(existing, newId)
    assert result == "test_3"


def test_increaseIdCounter_mixed_existing_ids():
    existing = ["test", "test_1", "other_test", "test_2"]
    newId = "test"
    result = increaseIdCounter(existing, newId)
    assert result == "test_3"


def test_increaseIdCounter_no_match_with_suffix():
    existing = ["test_1", "test_2", "test_3"]
    newId = "test_4"
    result = increaseIdCounter(existing, newId)
    assert result == "test_4"


def test_increaseIdCounter_existing_ids_with_suffix():
    existing = ["test_1", "test_2", "test_3"]
    newId = "test"
    result = increaseIdCounter(existing, newId)
    assert result == "test_4"


def test_increaseIdCounter_existing_ids_with_missing_entries():
    existing = ["test_1", "test", "test_3", "test_10"]
    newId = "test"
    result = increaseIdCounter(existing, newId)
    assert result == "test_11"

    existing = ["test_10"]
    newId = "test"
    result = increaseIdCounter(existing, newId)
    assert result == "test_11"


def test_increaseIdCounter_double_suffix():
    existing = ["test_1", "test_2", "test_3", "test_3_1", "test_3_2"]
    newId = "test_2"
    result = increaseIdCounter(existing, newId)
    assert result == "test_2_1"

    existing = ["test_1", "test_2", "test_3", "test_3_1", "test_3_2"]
    newId = "test_3"
    result = increaseIdCounter(existing, newId)
    assert result == "test_3_3"


def test_filter_sensors_no_filters():
    sensors = {
        "sensor1": ("backend1",),
        "sensor2": ("backend2",),
        "sensor3": ("backend1",),
    }
    result = filter_sensors(sensors)
    assert result == sensors


def test_filter_sensors_include_sensors():
    sensors = {
        "sensor1": ("backend1",),
        "sensor2": ("backend2",),
        "sensor3": ("backend1",),
    }
    include_sensors = ["sensor1", "sensor3"]
    result = filter_sensors(sensors, include_sensors=include_sensors)
    assert result == {"sensor1": ("backend1",), "sensor3": ("backend1",)}


def test_filter_sensors_exclude_sensors():
    sensors = {
        "sensor1": ("backend1",),
        "sensor2": ("backend2",),
        "sensor3": ("backend1",),
    }
    exclude_sensors = ["sensor2"]
    result = filter_sensors(sensors, exclude_sensors=exclude_sensors)
    assert result == {"sensor1": ("backend1",), "sensor3": ("backend1",)}


def test_filter_sensors_include_and_exclude_sensors():
    sensors = {
        "sensor1": ("backend1",),
        "sensor2": ("backend2",),
        "sensor3": ("backend1",),
    }
    include_sensors = ["sensor1", "sensor2"]
    exclude_sensors = ["sensor2"]
    result = filter_sensors(
        sensors, include_sensors=include_sensors, exclude_sensors=exclude_sensors
    )
    assert result == {"sensor1": ("backend1",), "sensor3": ("backend1",)}


def test_filter_sensors_include_backends():
    sensors = {
        "sensor1": ("backend1",),
        "sensor2": ("backend2",),
        "sensor3": ("backend1",),
    }
    include_backends = ["backend1"]
    result = filter_sensors(sensors, include_backends=include_backends)
    assert result == {"sensor1": ("backend1",), "sensor3": ("backend1",)}


def test_filter_sensors_exclude_backends():
    sensors = {
        "sensor1": ("backend1",),
        "sensor2": ("backend2",),
        "sensor3": ("backend1",),
    }
    exclude_backends = ["backend2"]
    result = filter_sensors(sensors, exclude_backends=exclude_backends)
    assert result == {"sensor1": ("backend1",), "sensor3": ("backend1",)}


def test_filter_sensors_include_and_exclude_backends():
    sensors = {
        "sensor1": ("backend1",),
        "sensor2": ("backend2",),
        "sensor3": ("backend1",),
    }
    include_backends = ["backend1", "backend2"]
    exclude_backends = ["backend2"]
    result = filter_sensors(
        sensors, include_backends=include_backends, exclude_backends=exclude_backends
    )
    assert result == {"sensor1": ("backend1",), "sensor3": ("backend1",)}
