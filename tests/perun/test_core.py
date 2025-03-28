from pathlib import Path

from perun.core import Perun
from perun.io.io import IOFormat, importFrom
from perun.monitoring.application import Application


def test_binary_app(tmp_path: Path, perun: Perun):
    resultPath = tmp_path / "results"

    app = Application("sleep", perun.config, is_binary=True, args=("10",))
    assert app.name == "sleep"
    assert app.args == ("10",)
    assert app.kwargs == {}
    assert app.is_binary

    if perun.comm.Get_size() == 1:
        perun.config.set("output", "data_out", str(resultPath))

        perun.monitor_application(app)

        resultFiles = list(resultPath.iterdir())
        assert len(resultFiles) == 2
        assert resultPath / "sleep.hdf5" in resultFiles
        assert (resultPath / "sleep.hdf5").is_file()

        resultFiles.remove(resultPath / "sleep.hdf5")
        textFile = resultFiles.pop()
        assert textFile.is_file()
        assert textFile.suffix == ".txt"


def test_multirun_id_set_correctly(tmp_path: Path, perun: Perun):
    resultPath = tmp_path / "results"
    perun.config.set("output", "data_out", str(resultPath))
    perun.config.set("output", "run_id", "test_multirun_id")

    app = Application("sleep", perun.config, is_binary=True, args=("1",))
    perun.monitor_application(app)

    resultFiles = list(resultPath.iterdir())
    assert resultPath / "sleep.hdf5" in resultFiles
    assert resultPath / "sleep_test_multirun_id.txt" in resultFiles

    # Verify that the multi-run ID was set correctly

    data_node = importFrom(resultPath / "sleep.hdf5", IOFormat.HDF5)
    assert data_node.id == "sleep"
    assert "test_multirun_id" in data_node.nodes.keys()


def test_script_error(tmp_path: Path, perun: Perun):
    resultPath = tmp_path / "results"
    perun.config.set("output", "data_out", str(resultPath))
    perun.config.set("output", "app_name", str("error"))
    perun.config.set("output", "run_id", "attempt")

    app = Application("./tests/scripts/error.py", perun.config)
    perun.monitor_application(app)

    resultFiles = list(resultPath.iterdir())
    assert resultPath / "failed_error.hdf5" in resultFiles
    assert len(resultFiles) == 2


def test_script_exit(tmp_path: Path, perun: Perun):
    resultPath = tmp_path / "results"
    perun.config.set("output", "data_out", str(resultPath))
    perun.config.set("output", "app_name", str("exit"))
    perun.config.set("output", "run_id", "dont")

    app = Application("./tests/scripts/exit.py", perun.config)
    perun.monitor_application(app)
