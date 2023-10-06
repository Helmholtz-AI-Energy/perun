"""Command line API."""
import argparse
import json
import logging
import sys
from pathlib import Path

import perun
from perun.configuration import config, read_custom_config, read_environ, save_to_config
from perun.io.io import IOFormat
from perun.perun import Perun

log = logging.getLogger("perun")


def cli():
    """Command line entrypoint."""
    parser = argparse.ArgumentParser(
        prog="perun",
        description="Distributed performance and energy monitoring tool",
        allow_abbrev=False,
    )
    parser.add_argument("-c", "--configuration", default="./.perun.ini")
    parser.add_argument(
        "-l", "--log_lvl", choice=["DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"]
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
        required=True,
        help="Existing perun output file. Should be hdf5, json or pickle.",
    )
    export_parser.add_argument(
        "format",
        dest="output_format",
        required=True,
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
        "--app_name",
        dest="app_name",
        help="Name o the monitored application. The name is used to distinguish between multiple application in the same directory. If left empty, the file name will be used.",
    )
    monitor_parser.add_argument(
        "-i",
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
        "--data_out",
        help="Directory where output files are saved. Defaults to ./perun_results",
    )
    monitor_parser.add_argument(
        "--sampling_rate", type=float, help="Sampling rate in seconds"
    )
    monitor_parser.add_argument(
        "--pue", type=float, help="Data center Power Usage Effectiveness"
    )
    monitor_parser.add_argument(
        "--price_factor",
        type=float,
        help="Electricity to Currency convertion factor in the form of Currency/kWh",
    )
    monitor_parser.add_argument(
        "--rounds", type=int, help="Number of warmup rounds to run app."
    )
    monitor_parser.add_argument(
        "--warmup_rounds",
        type=int,
        help="Number of warmup rounds to run the app. A warmup round is a full run of the application without gathering performance data.",
    )
    monitor_parser.add_argument("script", required=True, type=str)
    monitor_parser.add_argument("script_args", required=True, nargs=argparse.REMAINDER)
    monitor_parser.set_defaults(func=monitor)

    # parse and read conf file and env
    args, remaining = parser.parse_known_args()
    if args.configuration:
        read_custom_config(args.configuration)

    read_environ()

    if args.log_lvl:
        save_to_config("log_lvl", args.log_lvl)

    # set logging
    log.setLevel(config.get("debug", "log_lvl"))

    # start function
    args.func(args)


def showconf(args: argparse.Namespace):
    """Print current perun configuration in INI format."""
    from perun.configuration import _default_config

    if args.showconf_default:
        config.read_dict(_default_config)
        config.write(sys.stdout)
    else:
        config.write(sys.stdout)


def sensors(args: argparse.Namespace):
    """Print sensors assigned to each rank by perun."""
    perun = Perun(config)
    if perun.comm.Get_rank() == 0:
        for rank, bes in enumerate(perun.sensors_config):
            print(f"Rank: {rank}")
            for key, items in bes.items():
                if len(items) > 0:
                    print(f"   {key}:")
                    for device in items:
                        print(f"       {device}")
                    print("")

        print("Hostnames: ")
        for host, ranks in perun.host_rank.items():
            print(f"   {host}: {ranks}")


def metadata(args: argparse.Namespace):
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


def export(args: argparse.Namespace):
    """Export existing perun output file to another format."""
    in_file = Path(args.input_file)
    if not in_file.exists():
        log.error("File does not exist.")
        return -1

    perun = Perun(config)

    out_path = in_file.parent
    inputFormat = IOFormat.fromSuffix(in_file.suffix)
    out_format = IOFormat(args.output_format)

    dataNode = perun.import_from(in_file, inputFormat)
    if args.run_id:
        perun.export_to(out_path, dataNode, out_format, args.run_id)
    else:
        perun.export_to(out_path, dataNode, out_format)


def monitor(args: argparse.Namespace):
    """
    Gather power consumption from hardware devices while SCRIPT [SCRIPT_ARGS] is running.

    SCRIPT is a path to the python script to monitor, run with arguments SCRIPT_ARGS.
    """
    filePath: Path = Path(args.script)
    log.debug(f"Script path: {filePath}")
    argIndex = sys.argv.index(args.script)
    sys.argv = sys.argv[argIndex:]
    log.debug(f"Script args: { sys.argv }")

    # Setup script arguments
    for key, value in args.vars().items():
        save_to_config(key, value)

    perun = Perun(config)

    sys.path.insert(0, str(filePath.parent.absolute()))

    perun.monitor_application(filePath)
