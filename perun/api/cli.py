"""Command line API."""

import argparse
import json
import logging
import sys
from pathlib import Path

import perun
from perun.configuration import (
    config,
    read_custom_config,
    read_environ,
    sanitize_config,
    save_to_config,
)
from perun.core import MonitorStatus, Perun
from perun.io.io import IOFormat
from perun.io.text_report import sensors_table
from perun.logging import set_logger_config
from perun.monitoring.application import Application

log = logging.getLogger(__name__)

# The sensor/backend filter options are special: an explicitly provided empty
# string (or the literal "none") means "clear whatever value is set in the
# configuration file". This is the only way to remove the default excluded
# sensors from the command line.
CLEARABLE_OPTIONS = frozenset(
    {
        "include_sensors",
        "include_backends",
        "exclude_sensors",
        "exclude_backends",
    }
)


def _resolve_clearable_value(value: str | None) -> str | None:
    """Resolve the value of a clearable filter option.

    Parameters
    ----------
    value : str | None
        The raw value coming from the command line. ``None`` means the flag was
        not provided.

    Returns
    -------
    str | None
        ``None`` if the option should be left untouched (flag not provided),
        an empty string if the option should be cleared (empty string or the
        literal ``"none"`` was provided), otherwise the original value.
    """
    if value is None:
        return None
    if isinstance(value, str) and value.strip().lower() in {"", "none"}:
        return ""
    return value


def _get_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="perun",
        description="Distributed performance and energy monitoring tool",
        allow_abbrev=False,
    )
    parser.add_argument(
        "-c",
        "--configuration",
        default="./.perun.ini",
        help="Path to perun configuration file.",
    )
    parser.add_argument(
        "-l",
        "--log-lvl",
        "--log_lvl",
        dest="log_lvl",
        choices=["DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"],
        help="Logging level.",
    )
    parser.add_argument(
        "--log-file",
        "--log_file",
        dest="log_file",
        default=None,
        help="Path to the log file. None by default. Writting to a file disables logging in stdout.",
    )
    parser.add_argument(
        "--version", action="version", version=f"perun {perun.__version__}"
    )
    subparsers = parser.add_subparsers(dest="subcommand")

    # showconf
    showconf_parser = subparsers.add_parser(
        "showconf", help="Print perun configuration in INI format."
    )
    showconf_parser.add_argument(
        "--default",
        action="store_true",
        help="Print the default configuration",
        dest="showconf_default",
    )
    showconf_parser.set_defaults(func=showconf)

    # sensors
    sensor_parser = subparsers.add_parser(
        "sensors", help="Print available sensors by host and rank."
    )
    sensor_group = sensor_parser.add_mutually_exclusive_group()
    sensor_group.add_argument(
        "--all", help="Print all available sensors.", action="store_true"
    )
    sensor_group.add_argument(
        "--by-rank",
        "--by_rank",
        dest="by_rank",
        help="Print sensors by available on each rank.",
        action="store_true",
    )
    sensor_group.add_argument(
        "--active",
        help="Print active sensors by rank based on the configuration file.",
        action="store_true",
    )
    sensor_parser.set_defaults(func=sensors)

    # metadata
    metadata_parser = subparsers.add_parser(
        "metadata", help="Print available metadata."
    )
    metadata_parser.set_defaults(func=metadata)

    # export
    export_parser = subparsers.add_parser(
        "export", help="Export existing output file to another format."
    )
    export_parser.add_argument(
        "-i", "--id", dest="run_id", help="Run id to export, last one by default"
    )
    export_parser.add_argument(
        "input_file",
        help="Existing perun output file. Should be hdf5, json or pickle.",
    )
    export_parser.add_argument(
        "format",
        help="Desired data output format.",
    )
    export_parser.set_defaults(func=export)

    # monitor
    monitor_parser = subparsers.add_parser(
        "monitor",
        help="""
    Gather power consumption from hardware devices while SCRIPT [SCRIPT_ARGS] is running.

    SCRIPT is a path to the python script to monitor, run with arguments SCRIPT_ARGS.
    """,
    )
    monitor_parser.add_argument(
        "-n",
        "--app-name",
        "--app_name",
        dest="app_name",
        help="Name o the monitored application. The name is used to distinguish between multiple application in the same directory. If left empty, the file name will be used.",
    )
    monitor_parser.add_argument(
        "-i",
        "--run-id",
        "--run_id",
        dest="run_id",
        help="Unique id of the latest run of the application. If left empty, perun will use the current date.",
    )
    monitor_parser.add_argument(
        "-f",
        "--format",
        help="Secondary report format.",
        choices=[format.value for format in IOFormat],
    )
    monitor_parser.add_argument(
        "--data-out",
        "--data_out",
        dest="data_out",
        help="Directory where output files are saved. Defaults to ./perun_results",
    )
    monitor_parser.add_argument(
        "--sampling-period",
        "--sampling_period",
        dest="sampling_period",
        type=float,
        help="Sampling period in seconds. Defaults to 1 second.",
    )
    monitor_parser.add_argument(
        "--queue-timeout",
        "--queue_timeout",
        dest="queue_timeout",
        type=int,
        help="Seconds to wait for a result from the monitoring subprocess before considering it failed. Defaults to 60 seconds.",
    )
    monitor_parser.add_argument(
        "--include-sensors",
        "--include_sensors",
        dest="include_sensors",
        type=str,
        default=None,
        help="Space separated list of sensors to use. Defaults to an empty string (all available sensors). Pass an empty string (--include-sensors '') or 'none' to clear a value set in the configuration file.",
    )
    monitor_parser.add_argument(
        "--include-backends",
        "--include_backends",
        dest="include_backends",
        type=str,
        default=None,
        help="Space separated list of measuring backends to use. Defaults to an empty string (all available sensors). Pass an empty string (--include-backends '') or 'none' to clear a value set in the configuration file.",
    )
    monitor_parser.add_argument(
        "--exclude-sensors",
        "--exclude_sensors",
        dest="exclude_sensors",
        type=str,
        default=None,
        help="Space separated list of sensors to exclude. Perun excludes some noisy sensors by default. Pass an empty string (--exclude-sensors '') or 'none' to clear the default exclude list and monitor every sensor.",
    )
    monitor_parser.add_argument(
        "--exclude-backends",
        "--exclude_backends",
        dest="exclude_backends",
        type=str,
        default=None,
        help="Space separated list of measuring backends to exclude. Pass an empty string (--exclude-backends '') or 'none' to clear a value set in the configuration file.",
    )
    monitor_parser.add_argument(
        "--power-overhead",
        "--power_overhead",
        dest="power_overhead",
        type=float,
        help="Estimated power consumption of non-measured hardware components in Watts. Will be added to measured power consumption on the text report summary. Defaults to 0 Watts",
    )
    monitor_parser.add_argument(
        "--pue", type=float, help="Data center Power Usage Effectiveness. Defaults to 1"
    )
    monitor_parser.add_argument(
        "--price-factor",
        "--price_factor",
        dest="price_factor",
        type=float,
        help="Electricity to Currency convertion factor in the form of Currency/kWh. Defaults to 0.3251 €/kWh",
    )
    monitor_parser.add_argument(
        "--price-unit",
        "--price_unit",
        dest="price_unit",
        type=str,
        help="Currency character to use on the text report summary. Defaults to €",
    )
    monitor_parser.add_argument(
        "--emission-factor",
        "--emission_factor",
        dest="emission_factor",
        type=float,
        help="Average carbon intensity of electricity (gCO2e/kWh). Defaults to 417.80 gC02e/kWh",
    )
    monitor_parser.add_argument(
        "--rounds", type=int, help="Number of warmup rounds to run app. Defaults to 1"
    )
    monitor_parser.add_argument(
        "--warmup-rounds",
        "--warmup_rounds",
        dest="warmup_rounds",
        type=int,
        help="Number of warmup rounds to run the app. A warmup round is a full run of the application without gathering performance data. Defaults to 0",
    )
    monitor_parser.add_argument(
        "--bench-metrics",
        "--bench_metrics",
        dest="metrics",
        type=str,
        help="List of metrics to add to the benchmark results. Only relevant when using the 'bench' format. Defaults to 'runtime,energy'",
    )
    monitor_parser.add_argument(
        "--region-metrics",
        "--region_metrics",
        dest="region_metrics",
        type=str,
        help="List of metrics to add to the benchmark results that are associated with individual regions. Only relevant when using the 'bench' format. Defaults to 'runtime,energy'",
    )
    monitor_parser.add_argument(
        "-b",
        "--binary",
        action="store_true",
        help="Indicate if the monitored application is a binary. Otherwise treat it as a python script.",
    )
    monitor_parser.add_argument(
        "--live-callback-files",
        "--live_callback_files",
        nargs="+",
        default=[],
        dest="live_callback_files",
        type=argparse.FileType("r", encoding="utf-8"),
        help="Path to file that contains the live callbacks to use.",
    )
    monitor_parser.add_argument("cmd", type=str)
    monitor_parser.add_argument("cmd_args", nargs=argparse.REMAINDER)
    monitor_parser.set_defaults(func=monitor)
    return parser


def cli() -> None:
    """Command line entrypoint."""
    parser = _get_arg_parser()

    # parse and read conf file and env
    args, remaining = parser.parse_known_args()

    if args.subcommand is None:
        parser.print_help()
        return

    # 1) Read custom configuration
    if args.configuration:
        read_custom_config(args.configuration)

    # 2) Read environment variables
    read_environ()

    # 3) Parse remaining arguments
    for key, value in vars(args).items():
        if key in CLEARABLE_OPTIONS:
            resolved = _resolve_clearable_value(value)
            if resolved is not None:
                save_to_config(key, resolved)
        elif value:
            save_to_config(key, value)

    sanitize_config(config)
    set_logger_config(config)

    # start function
    if hasattr(args, "func"):
        args.func(args)


def showconf(args: argparse.Namespace) -> None:
    """Print current perun configuration in INI format."""
    from perun.configuration import _default_config

    if args.showconf_default:
        config.read_dict(_default_config)
        config.write(sys.stdout)
    else:
        config.write(sys.stdout)


def sensors(args: argparse.Namespace) -> None:
    """Print available sensors."""
    perun = Perun(config)
    log.debug("Initialized perun object.")
    arg_by_rank = args.by_rank
    arg_active = args.active

    if arg_by_rank:
        log.debug("Printing sensors by rank.")
        g_available_sensors = perun.g_available_sensors
        if perun.comm.Get_rank() == 0:
            print(sensors_table(g_available_sensors))
    elif arg_active:
        log.debug("Printing active sensors by rank.")
        g_assigned_sensors = perun.g_assigned_sensors
        if perun.comm.Get_rank() == 0:
            print(sensors_table(g_assigned_sensors))
    else:
        log.debug("Printing all available sensors.")
        g_available_sensors = perun.g_available_sensors
        available_sensors: dict[str, tuple] = {}
        for _, sensors in enumerate(g_available_sensors):
            available_sensors.update(sensors)
        if perun.comm.Get_rank() == 0:
            print(sensors_table([available_sensors], by_rank=False))


def metadata(args: argparse.Namespace) -> None:
    """Print global metadata dictionaries in json format."""
    perun = Perun(config)

    hostMD = perun.l_host_metadata
    hostMD["backends"] = perun.l_backend_metadata
    allHostsMD = perun.comm.gather(hostMD, root=0)

    if perun.comm.Get_rank() == 0 and allHostsMD:
        metadataDict = {}
        for host, assignedRanks in perun.host_rank.items():
            metadataDict[host] = allHostsMD[assignedRanks[0]]

        json.dump(metadataDict, sys.stdout, indent=4)


def export(args: argparse.Namespace) -> None:
    """Export existing perun output file to another format."""
    in_file = Path(args.input_file)
    if not in_file.exists():
        log.error("File does not exist.")
        return

    perun = Perun(config)

    out_path = in_file.parent
    inputFormat = IOFormat.fromSuffix(in_file.suffix)
    out_format = IOFormat(args.format)

    dataNode = perun.import_from(in_file, inputFormat)
    if args.run_id:
        perun.export_to(out_path, dataNode, out_format, args.run_id)
    else:
        perun.export_to(out_path, dataNode, out_format)


def monitor(args: argparse.Namespace) -> None:
    """
    Gather power consumption from hardware devices while SCRIPT [SCRIPT_ARGS] is running.

    SCRIPT is a path to the python script to monitor, run with arguments SCRIPT_ARGS.
    """
    cmd: str = args.cmd
    log.debug(f"Cmd: {cmd}")
    argIndex = sys.argv.index(args.cmd)
    sys.argv = sys.argv[argIndex:]
    cmd_args: list[str] = sys.argv.copy()
    log.debug(f"Cmd args: {cmd_args}")
    if not args.binary:
        scriptPath = Path(cmd)
        try:
            assert scriptPath.exists()
            assert scriptPath.is_file()
            assert scriptPath.suffix == ".py"
        except AssertionError:
            log.error(
                f"Invalid script path. File {scriptPath} does not exist or is not a python script."
            )

        sys.path.insert(0, str(scriptPath.parent.absolute()))
        app = Application(scriptPath, config, args=tuple(sys.argv[1:]))
    else:
        app = Application(cmd, config, is_binary=True, args=tuple(sys.argv[1:]))

    perun = Perun(config)
    for live_callback_file in args.live_callback_files:
        log.info(f"Loading live callback from file: {live_callback_file.name}")
        try:
            # Load the files using importlib
            live_callback_code = live_callback_file.read()
            exec(live_callback_code, globals(), locals())
            log.info("Live callback loaded successfully.")
        except Exception as e:
            log.error(
                f"Error loading live callback from file {live_callback_file.name}: {e}"
            )
            continue

    log.info("Starting perun monitoring application.")

    exit_status, _ = perun.monitor_application(app)
    log.info(f"Monitoring finished with status {exit_status}. Exiting.")
    if exit_status not in [
        MonitorStatus.PROCESSING,
        MonitorStatus.READY,
        MonitorStatus.CLOSED,
    ]:
        exit(1)
