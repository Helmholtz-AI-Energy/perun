"""Command line api definition.

Uses click https://click.palletsprojects.com/en/8.1.x/ to manage complex cmdline configurations.
"""
from pathlib import Path
from pprint import pprint

import click

import perun
from perun import log
from perun.configuration import config, read_custom_config, save_to_config_callback
from perun.io.io import IOFormat, exportTo, importFrom


@click.group()
@click.version_option(version=perun.__version__)
@click.option(
    "-c",
    "--configuration",
    default="./.perun.ini",
    help="Path to configuration file",
    type=click.Path(exists=False, dir_okay=False, readable=True),
    is_eager=True,
    callback=read_custom_config,
    expose_value=False,
)
# Output option
@click.option(
    "-n",
    "--app_name",
    help="Name of the monitored application. The name is used to distinguish between multiple applications in the same directory. If left empty, the filename will be  used.",
    callback=save_to_config_callback,
    expose_value=False,
)
@click.option(
    "-i",
    "--run_id",
    help="Unique id of the latest run of the application. If left empty, perun will use the SLURM job id, or the current date.",
    callback=save_to_config_callback,
    expose_value=False,
)
@click.option(
    "--format",
    type=click.Choice([format.value for format in IOFormat]),
    help="Report format.",
    callback=save_to_config_callback,
    expose_value=False,
)
@click.option(
    "--data_out",
    type=click.Path(exists=False, dir_okay=True, file_okay=False),
    help="Where to save the output files, defaults to the current working directory.",
    callback=save_to_config_callback,
    expose_value=False,
)
@click.option(
    "--raw",
    default=False,
    help="Use the flag '--raw' if you need access to all the raw data collected by perun. The output will be saved on an hdf5 file on the perun data output location.",
    is_flag=True,
    callback=save_to_config_callback,
    expose_value=False,
)
# Sampling Options
@click.option(
    "--sampling_rate",
    type=float,
    help="Sampling rate in seconds.",
    callback=save_to_config_callback,
    expose_value=False,
)
# Post processing options
@click.option(
    "--pue",
    type=float,
    help="Data center Power Usage Efficiency.",
    callback=save_to_config_callback,
    expose_value=False,
)
@click.option(
    "--emissions_factor",
    type=float,
    help="Emissions factor at compute resource location.",
    callback=save_to_config_callback,
    expose_value=False,
)
@click.option(
    "--price_factor",
    type=float,
    help="Electricity price factor at compute resource location.",
    callback=save_to_config_callback,
    expose_value=False,
)
# Benchmarking
@click.option(
    "--bench",
    "bench_enable",
    is_flag=True,
    help="Activate benchmarking mode.",
    callback=save_to_config_callback,
    expose_value=False,
)
@click.option(
    "--bench_rounds",
    type=int,
    help="Number of rounds per function/app.",
    callback=save_to_config_callback,
    expose_value=False,
)
@click.option(
    "--bench_warmup_rounds",
    type=int,
    help="Number of warmup rounds per function/app.",
    callback=save_to_config_callback,
    expose_value=False,
)
# @click.option(
#     "--bench_metrics",
#     multiple=True,
#     help="Metrics to output. Only relevant with bench_minimal_format enabled",
#     callback=save_to_config_callback,
#     expose_value=False,
# )
# Debug Options
@click.option(
    "-l",
    "--log_lvl",
    type=click.Choice(["DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"]),
    help="Loggging level",
    callback=save_to_config_callback,
    expose_value=False,
)
def cli():
    """Perun: Energy measuring and reporting tool."""
    log.setLevel(config.get("debug", "log_lvl"))


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
def sensors():
    """Print sensors assigned to each rank by perun."""
    from perun import COMM_WORLD
    from perun.backend import backends
    from perun.coordination import getGlobalSensorRankConfiguration

    globalHostRank, globalSensorConfig = getGlobalSensorRankConfiguration(
        COMM_WORLD, backends
    )
    if COMM_WORLD.Get_rank() == 0:
        for rank, bes in enumerate(globalSensorConfig):
            click.echo(f"Rank: {rank}")
            click.echo(pprint(bes))

        click.echo("Hostnames: ")
        click.echo(pprint(globalHostRank))

    for b in backends:
        b.close()


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.argument("output_path", type=click.Path(exists=True))
@click.argument(
    "output_format",
    type=click.Choice([format.value for format in IOFormat]),
)
def export(input_file: str, output_path: str, output_format: str):
    """Export existing perun output file to another format."""
    in_file = Path(input_file)
    if not in_file.exists():
        click.echo("File does not exist.", err=True)
        return

    out_path = Path(output_path)
    if not out_path.parent.exists():
        click.echo("Output path does not exist", err=True)
        return

    inputFormat = IOFormat.fromSuffix(in_file.suffix)
    out_format = IOFormat(output_format)
    dataNode = importFrom(in_file, inputFormat)
    exportTo(out_path, dataNode, out_format, rawData=True)


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
    # Setup script arguments
    import sys

    from perun.perun import monitor_application

    filePath: Path = Path(script)
    log.debug(f"Script path: {filePath}")
    argIndex = sys.argv.index(script)
    sys.argv = sys.argv[argIndex:]
    log.debug(f"Script args: { sys.argv }")

    sys.path.insert(0, str(filePath.parent.absolute()))

    monitor_application(filePath)


def main():
    """Cli entrypoint."""
    cli(auto_envvar_prefix="PERUN")
