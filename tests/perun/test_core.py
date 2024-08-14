from pathlib import Path

from perun.core import Perun
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
