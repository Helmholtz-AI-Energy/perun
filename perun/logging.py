"""Logging utilities."""

import logging
import logging.config


def init_logging(level: str) -> logging.Logger:
    """Initialize logging object.

    Parameters
    ----------
    level : str
        Logging level

    Returns
    -------
    Logger
        Logger object
    """
    logConfig = {
        "version": 1,
        "loggers": {"perun": {"level": level, "handlers": ["console"]}},
        "handlers": {
            "console": {
                "formatter": "std_out",
                "class": "logging.StreamHandler",
                "level": "DEBUG",
                "stream": "ext://sys.stdout",
            }
        },
        "formatters": {
            "std_out": {
                "format": "%(asctime)s : %(levelname)s : %(module)s : %(funcName)s -- %(message)s",
                "datefmt": "%d-%m-%Y %I:%M:%S",
            }
        },
    }
    logging.config.dictConfig(logConfig)
    return logging.getLogger("perun")
