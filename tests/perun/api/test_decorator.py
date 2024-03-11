import subprocess
import time
from pathlib import Path

import pytest

import perun
from perun.api.decorator import monitor, perun, register_callback
from perun.data_model.data import DataNode


def test_perun_cli(tmp_path: Path):
    # Test case for perun decorator
    # Add your test logic here

    testFilePath = Path("./tests/scripts/sleep_decorated.py")
    resultsPath = tmp_path / "results/"

    subprocess.run(
        f"PERUN_DATA_OUT={str(resultsPath)} python {testFilePath}".split(" "),
        timeout=20,
    )

    # Expected files, hdf5 file and a text file with a date
    # Are the files in the correct folder
    resultFiles = list(resultsPath.iterdir())
    assert len(resultFiles) == 2
    assert resultsPath / "sleep.hdf5" in resultFiles
    assert (resultsPath / "sleep.hdf5").is_file()

    resultFiles.remove(resultsPath / "sleep.hdf5")
    textFile = resultFiles.pop()
    assert textFile.is_file()
    assert textFile.suffix == ".txt"


def test_perun_decorator(tmp_path: Path):

    results_path = tmp_path / "results"

    @perun.perun(data_out=results_path)
    def perun_sleep(secs: int):
        time.sleep(secs)

    # Run function
    perun_sleep(10)

    # Expected files, hdf5 file and a text file with a date
    # Are the files in the correct folder
    resultFiles = list(results_path.iterdir())
    assert len(resultFiles) == 2
    assert results_path / "perun_sleep.hdf5" in resultFiles
    assert (results_path / "perun_sleep.hdf5").is_file()

    resultFiles.remove(results_path / "perun_sleep.hdf5")
    textFile = resultFiles.pop()
    assert textFile.is_file()
    assert textFile.suffix == ".txt"
