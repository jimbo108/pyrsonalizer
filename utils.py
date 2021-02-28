"""Contains convenience functions."""
import logging
from typing import Callable, Type, Optional, Any, Dict, Union
import os

import yaml

import errors
import logging
import pathlib


def get_config(path: Union[pathlib.Path, os.PathLike], logger: logging.Logger) -> Dict[str, Any]:
    if not os.path.exists(path):
        log_and_raise(
            logger.error,
            ValueError,
            f"Path {str(path)} does not exist.",
            errors.GP_PATH_DOES_NOT_EXIST,
        )

    with open(path) as fh:
        return yaml.load(fh, Loader=yaml.BaseLoader)


def log_and_raise(
    logger_func: Callable,
    exception: Type[BaseException],
    error_message: str,
    error_key: Optional[str] = None,
) -> None:
    """Log `error_message` and using `logger_func` and raise `exception.

    Args:
         logger_func: The warn/error/info etc. function from the calling module's
            logger.
        exception: The exception type to raise.
        error_message: The error_message to log using `logger_func`.
        error_key: A unique error key per calling location. See errors.py for
            explanation
    """
    if error_key is not None:
        error_message = error_key + ": "
    logger_func(error_message)
    raise exception
