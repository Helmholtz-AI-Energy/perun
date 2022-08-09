"""Command line api definition.

Uses click https://click.palletsprojects.com/en/8.1.x/ to manage complex cmdline configurations.
"""
import click


@click.group()
@click.option(
    "-l",
    "--log_lvl",
    "log_lvl",
    type=click.Choice(["DEBUG", "INFO", "WARN"]),
    default="INFO",
)
def cli(log_lvl: str):
    """
    Entry point for the perun command line interface.

    Args:
        log_lvl (str): Desired stdout log level
    """
    from perun.logging import init_logging

    init_logging(log_lvl)


@cli.command(context_settings={"ignore_unknown_options": True})
@click.argument("filepath", type=click.Path(exists=True))
@click.argument("script_args", nargs=-1)
@click.option("-f", "--frequency", type=int, default=1)
def monitor(filepath: str, script_args: tuple, frequency: int):
    """
    Monitor the energy consumption of a python script.

    Args:
        script: File containg the script to be monitored
        args: cmdline arguments of the script
        frecuency: how often to sample measurments
    """


if __name__ == "__main__":
    cli()
