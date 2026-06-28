import logging
from typing import Literal

from colorama import Fore, Style


class LoggerFormatter(logging.Formatter):
    def format(self, record):
        italic = "\033[3m"
        bold = "\033[1m"

        level_colors = {
            "CRITICAL": {"levelname": Fore.RED, "message": Fore.RED},
            "ERROR": {"levelname": Fore.RED, "message": Fore.RED},
            "WARNING": {"levelname": Fore.YELLOW, "message": Fore.YELLOW},
            "INFO": {"levelname": Fore.CYAN, "message": Fore.WHITE},
            "DEBUG": {"levelname": Fore.BLUE, "message": italic + Fore.BLUE},
        }

        if record.levelname in level_colors:
            format = (
                f"{Fore.GREEN}%(asctime)s{Style.RESET_ALL} "
                + f"{bold + level_colors[record.levelname]['levelname']}%(levelname)s{Style.RESET_ALL} "
                + f"{Fore.MAGENTA}%(name)s{Style.RESET_ALL} "
                + f"{Fore.BLUE}%(funcName)s %(filename)s:%(lineno)d{Style.RESET_ALL} "
                + f"{level_colors[record.levelname]['message']}%(message)s{Style.RESET_ALL}"
            )
        else:
            format = "%(asctime)s %(levelname)s %(name)s %(funcName)s %(filename)s:%(lineno)d %(message)s"

        formatter = logging.Formatter(fmt=format, datefmt="%Y-%m-%d %H:%M:%S")

        return formatter.format(record)


def configure_root_logger(level: Literal["NOTSET", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(getattr(logging, level, logging.INFO))

    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(LoggerFormatter())
        root.addHandler(handler)


def initialize_logger(
    name: str,
    level: Literal["NOTSET", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO",
    frmt: str | logging.Formatter | None = None,
    propagate: bool = False,
) -> logging.Logger:
    """Initialize a logger with the given name, level, format, and propagation."""
    if frmt is None:
        frmt = LoggerFormatter()

    level = getattr(logging, level, logging.INFO)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = propagate

    handler = logging.StreamHandler()
    if isinstance(frmt, str):
        handler.setFormatter(logging.Formatter(frmt))
    elif isinstance(frmt, logging.Formatter):
        handler.setFormatter(frmt)
    else:
        raise ValueError("Invalid format for 'frmt'.")

    if not logger.handlers:
        logger.addHandler(handler)

    return logger
