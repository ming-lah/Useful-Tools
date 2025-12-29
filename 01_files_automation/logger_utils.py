import logging
import sys
from pathlib import Path
from typing import Optional

def setup_logging(
    log_file_path: Optional[Path],
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
    logger_name: str = "filesorter",
) -> logging.Logger:
    
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        logger.handlers.clear()
    logger.propagate = False
    
    file_fmt = logging.Formatter(
        fmt="%(asctime)s - [%(levelname)s] - %(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_fmt = logging.Formatter(fmt="%(asctime)s - [%(levelname)s] - %(message)s")

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(console_fmt)
    logger.addHandler(console_handler)

    if log_file_path is not None:
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
        file_handler.setLevel(file_level)
        file_handler.setFormatter(file_fmt)
        logger.addHandler(file_handler)

    return logger