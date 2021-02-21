import logging
from typing import Callable


def log_and_raise(
    logger_func: Callable, exception: BaseException, error_message: str
) -> None:
    logger_func(error_message)
    raise exception
