"""Command line api definition.

Uses click https://click.palletsprojects.com/en/8.1.x/ to manage complex cmdline configurations.
"""
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import click

import perun
from perun import log
from perun.configuration import config, read_custom_config, save_to_config_callback


@click.group()
@click.version_option(version=perun.__version__)
@click.option(
    "-c",
    "--configuration",
    default="./.perun.ini",
    type=click.Path(exists=False, dir_okay=False, readable=True),
    is_eager=True,
    callback=read_custom_config,
    expose_value=False,
)
@click.option(
    "-f",
    "--format",
    type=click.Choice(["txt", "yaml", "yml", "json"]),
    help="report print format",
    callback=save_to_config_callback,
    expose_value=False,
)
@click.option(
    "-f",
    "--frequency",
    type=float,
    help="sampling frequency (in Hz)",
    callback=save_to_config_callback,
    expose_value=False,
)
@click.option(
    "--format",
    type=click.Choice(["txt", "yaml", "yml", "json"]),
    help="report print format",
    callback=save_to_config_callback,
    expose_value=False,
)
@click.option(
    "--data_out",
    type=click.Path(exists=False, dir_okay=True, file_okay=False),
    help="experiment data output directory",
    callback=save_to_config_callback,
    expose_value=False,
)
@click.option(
    "-l",
    "--log_lvl",
    type=click.Choice(["DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"]),
    help="Loggging level",
    callback=save_to_config_callback,
    expose_value=False,
)
@click.option(
    "--pue",
    type=float,
    help="Data center Power usage efficiency",
    callback=save_to_config_callback,
    expose_value=False,
)
@click.option(
    "--emissions-factor",
    type=float,
    help="Emissions factor at compute resource location",
    callback=save_to_config_callback,
    expose_value=False,
)
@click.option(
    "--price-factor",
    type=float,
    help="Electricity price factor at compute resource location",
    callback=save_to_config_callback,
    expose_value=False,
)
def cli():
    """Perun: Energy measuring and reporting tool."""
    log.setLevel(config.get("perun", "log_lvl"))


@cli.command()
@click.option(
    "--default",
    is_flag=True,
    show_default=True,
    default=False,
    help="Print default configuration",
)
def showconf(default: bool):
    """Print current perun configuration in INI format."""
    import sys

    from perun.configuration import _default_config

    if default:
        config.read_dict(_default_config)
        config.write(sys.stdout)
    else:
        config.write(sys.stdout)


@cli.command()
@click.argument("exp_hdf5", type=click.Path(exists=True))
def postprocess(exp_hdf5: str):
    """
    Apply post-processing to EXP_HDF5 experiment file.

    EXP_HDF5 is an hdf5 file generated by perun after monitoring a script, containing data gathered from hardware devices.
    """
    from mpi4py import MPI

    from perun.perun import postprocessing
    from perun.storage import ExperimentStorage

    expPath = Path(exp_hdf5)
    expStrg = ExperimentStorage(expPath, MPI.COMM_WORLD, write=True)
    postprocessing(expStrg, reset=True)
    expStrg.close()


@cli.command()
@click.argument("exp_hdf5", type=click.Path(exists=True))
def report(exp_hdf5: str):
    """Print consumption report from EXP_HDF5 on the command line on the desired format.

    EXP_HDF5 is an hdf5 file generated by perun after monitoring a script, containing data gathered from hardware devices.
    """
    from mpi4py import MPI

    from perun.report import report as _report
    from perun.storage import ExperimentStorage

    expPath = Path(exp_hdf5)
    expStrg = ExperimentStorage(expPath, MPI.COMM_WORLD)
    print(_report(expStrg, format=config.get("report", "format")))
    expStrg.close()


@cli.command(context_settings={"ignore_unknown_options": True})
@click.argument("script", type=click.Path(exists=True))
@click.argument("script_args", nargs=-1)
def monitor(
    script: str,
    script_args: tuple,
):
    """
    Gather power consumption from hardware devices while SCRIPT [SCRIPT_ARGS] is running.

    SCRIPT is a path to the python script to monitor, run with arguments SCRIPT_ARGS.
    """
    import sys
    from multiprocessing import Event, Process, Queue

    from mpi4py import MPI

    from perun import log
    from perun.backend import backends
    from perun.perun import getDeviceConfiguration, perunSubprocess, save_data
    from perun.storage import LocalStorage

    comm = MPI.COMM_WORLD
    start_event = Event()
    stop_event = Event()

    # Setup script arguments
    filePath: Path = Path(script)
    outPath: Path = Path(config.get("monitor", "data_out"))
    log.debug(f"Script path: {filePath}")
    argIndex = sys.argv.index(str(filePath))
    sys.argv = sys.argv[argIndex:]
    log.debug(f"Script args: { sys.argv }")

    # Get node devices
    log.debug(f"Backends: {backends}")
    lDeviceIds: List[str] = getDeviceConfiguration(comm, backends)

    for backend in backends:
        backend.close()

    log.debug(f"Rank {comm.rank} - lDeviceIds : {lDeviceIds}")

    # If assigned devices, start subprocess
    if len(lDeviceIds) > 0:
        queue: Queue = Queue()
        perunSP = Process(
            target=perunSubprocess,
            args=[
                queue,
                start_event,
                stop_event,
                lDeviceIds,
                config.getfloat("monitor", "frequency"),
            ],
        )
        perunSP.start()
        start_event.wait()

    # Sync everyone
    comm.barrier()
    start = datetime.now()

    # Start script
    try:
        with open(str(filePath), "r") as scriptFile:
            exec(scriptFile.read(), {"__name__": "__main__"})
    except Exception as e:
        log.error("Failed to open file ", filePath)
        log.error(e)
        stop_event.set()
        return

    stop_event.set()
    log.debug("Set closed event")
    stop = datetime.now()

    lStrg: Optional[LocalStorage]
    # Obtain perun subprocess results
    if len(lDeviceIds) > 0:
        log.debug("Getting queue contents")
        lStrg = queue.get(block=True)
        log.debug("Got queue contents")
        log.debug("Waiting for subprocess to close")
        perunSP.join()
        perunSP.close()
        log.debug("Subprocess closed")
        queue.close()
    else:
        lStrg = None

    # Sync
    comm.barrier()
    log.debug("Passed first barrier")

    # Save raw data to hdf5
    save_data(comm, outPath, filePath, lStrg, start, stop)


def main():
    """Cli entrypoint."""
    cli(auto_envvar_prefix="PERUN")
