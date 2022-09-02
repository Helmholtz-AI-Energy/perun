"""Report module."""
import json

import yaml

from perun.storage import ExperimentStorage


def report(
    expStrg: ExperimentStorage,
    format: str = "txt",
    expIdx: int = None,
    rawData: bool = False,
) -> str:
    """
    Generate report from ExperimentStorage object.

    Args:
        expStrg (ExperimentStorage): Storage object
        format (str, optional): Report format. Defaults to "txt".
        expIdx (int, optional): Index of experiment run (only relevant with text format). Defaults to None.
        rawData (bool, optional): If raw data should be included. Defaults to False.

    Raises:
        ValueError: _description_

    Returns:
        str: Report string
    """
    if format == "json":
        return json.dumps(expStrg.toDict(rawData), indent=4)
    elif format == "yml" or format == "yaml":
        return yaml.dump(expStrg.toDict(rawData))
    elif format == "txt":
        return _textReport(expStrg, expIdx)
    else:
        raise ValueError("Invalid report format")


def _textReport(expStrg: ExperimentStorage, expIdx: int = None) -> str:
    """
    Create text report from storage object.

    Args:
        expStrg (ExperimentStorage): Storage object
        expIdx (int, optional): Run to get information from. Defaults to -1 (last one)

    Returns:
        str: txt report
    """
    expIdx = expIdx if expIdx else expStrg.getLastExperimentIndex()
    run = expStrg.getExperimentRun(expIdx)
    reportStr = (
        "\n------------------------------------------\n"
        "PERUN REPORT\n"
        "\n"
        f"Experiment name: {expStrg.experimentName}\n"
        f"Run number: {expIdx}\n"
        f"Runtime: {run.attrs['totalRunRuntime_s']:.3f}s\n"
        f"Avg. Power draw: {run.attrs['runAvgPower_kW']:.3f}kW\n"
        f"Energy Used: {run.attrs['totalRunEnergy_kWh']:.3f}kWh\n"
        f"CO\N{SUBSCRIPT TWO}e : {run.attrs['totalRunCO2e_kg']:.3f}kg\n"
        f"Cost €: {run.attrs['totalRunPrice_euro']:.3f}€\n"
        "\n"
    )

    # Print last run info

    for node_id, node in run.items():
        reportStr += f"Node {node_id}\n"
        for device_id, device in node.items():
            if device_id != "t_ns" and device.attrs["units"] in ["Joule", "Watt"]:
                reportStr += f"    {device_id} - Energy: {device.attrs['totalDeviceEnergy_kJ']:.3f}kJ - AvgPower: {device.attrs['avgDevicePower_kW']:.3f}kW\n"
        reportStr += "\n"

    # Print experiment info
    nRuns = len(expStrg.getExperimentRuns())
    totalEnergy_kWh = expStrg.getRootObject().attrs["totalExpEnergy_kWh"]
    totalCO2_kg = expStrg.getRootObject().attrs["totalExpCO2e_kg"]
    totalPrice_euro = expStrg.getRootObject().attrs["totalExpPrice_euro"]
    reportStr += f"The script has been run a total {nRuns} times, has used {totalEnergy_kWh:.3f}kWh, generated {totalCO2_kg:.3f}kg of CO\N{SUBSCRIPT TWO}e and costed {totalPrice_euro:.3f}€"
    return reportStr
