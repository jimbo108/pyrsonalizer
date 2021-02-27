import logging
from typing import Callable, Type, Optional


def log_and_raise(
    logger_func: Callable, exception: Type[BaseException], error_message: str, error_key: Optional[str] = None
) -> None:
    if error_key is not None:
        error_message = error_key + ": "
    logger_func(error_message)
    raise exception
