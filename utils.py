"""Contains convenience functions."""
import logging
from typing import Callable, Type, Optional, Any, Dict, Union
import os

import yaml

import errors
import logging
import pathlib


logger = logging.Logger(__file__)

def get_config(
    path: Union[pathlib.Path, os.PathLike], logger: logging.Logger
) -> Dict[str, Any]:
    if not os.path.exists(path):
        log_and_raise(logger.error, f"Path {str(path)} does not exist.", ValueError, errors.GP_PATH_DOES_NOT_EXIST)

    with open(path) as fh:
        return yaml.load(fh, Loader=yaml.BaseLoader)


def log_and_raise(logger_func: Callable, error_message: str, exception: Union[Type[BaseException], BaseException],
                  error_key: Optional[str] = None) -> None:
    """Log `error_message` and using `logger_func` and raise `exception.

    Args:
         logger_func: The warn/error/info etc. function from the calling module's
            logger.
        error_message: The error_message to log using `logger_func`.
        exception: The exception type or exception instance to raise.
        error_key: A unique error key per calling location. See errors.py for
            explanation
    """
    if error_key is not None:
        error_message = error_key + ": " + error_message

    logger_func(error_message)
    raise exception

