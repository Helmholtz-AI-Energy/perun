"""Logging utilities."""

import logging
import pathlib
import sys
from configparser import ConfigParser

RESET_SEQ = "\033[0m"
COLOR_SEQ = "\033[1;%dm"
BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)

COLORS = {
    "WARNING": YELLOW,
    "INFO": WHITE,
    "DEBUG": GREEN,
    "CRITICAL": RED,
    "ERROR": RED,
}


class ColoredFormatter(logging.Formatter):
    """A logging formatter that adds colors to specific parts of the log message."""

    def format(self, record: logging.LogRecord) -> str:
        """Apply color formating to log message."""
        levelname = record.levelname
        color_level = COLOR_SEQ % (30 + COLORS.get(levelname, 0))
        record.levelname = f"{color_level}{levelname}{RESET_SEQ}"

        # Add colors to specific fields
        record.asctime = (
            f"{COLOR_SEQ % (30 + GREEN)}{self.formatTime(record)}{RESET_SEQ}"
        )
        record.name = f"{COLOR_SEQ % (30 + CYAN)}{record.name}{RESET_SEQ}"
        record.funcName = f"{COLOR_SEQ % (30 + MAGENTA)}{record.funcName}{RESET_SEQ}"
        record.msg = f"{color_level}{record.msg}{RESET_SEQ}"

        return super().format(record)


def set_logger_config(config: ConfigParser) -> None:
    """
    Configure the logging settings for the application.

    Parameters
    ----------
    config: ConfigParser
        Configuration object.

    Returns
    -------
    None
    """
    # Get logging configuration
    log_lvl = config.get("debug", "log_lvl")
    log_file = config.get("debug", "log_file")

    try:
        from mpi4py import MPI

        rank = f"R{MPI.COMM_WORLD.Get_rank()}/{MPI.COMM_WORLD.Get_size()}:"
    except ImportError:
        rank = ""

    base_logger = logging.getLogger("perun")
    format_string = (
        f"[%(asctime)s][%(name)s][%(funcName)s][%(levelname)s] - {rank}%(message)s"
    )

    simple_formatter = logging.Formatter(fmt=format_string)

    # Std out
    if log_file is None:
        std_handler = logging.StreamHandler(stream=sys.stdout)
        formatter = ColoredFormatter(fmt=format_string)
        std_handler.setFormatter(formatter)
        base_logger.addHandler(std_handler)
    else:
        log_path = pathlib.Path(log_file)
        log_dir = log_path.parents[0]
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(filename=log_path)
        file_handler.setFormatter(simple_formatter)
        base_logger.addHandler(file_handler)

    base_logger.setLevel(log_lvl)
