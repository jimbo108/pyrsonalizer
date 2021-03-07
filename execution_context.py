from typing import Dict, Any, Optional
import pathlib
from dataclasses import dataclass

import const

DEFAULT_PYRS_DIR = "~/.pyrsonalizer/"


@dataclass
class ExecutionContext:
    """A dataclass for holding state required for Action execution"""
    pyrsonalizer_directory: Optional[pathlib.Path] = None


def create_execution_context(config: Dict[str, Any]) -> ExecutionContext:
    """Creates an execution context.

    This is really sort of a cheat to pass some global context like app directory
    to the `Action.execute` methods.
    """
    pyrs_dir = config.get(const.PYRS_DIR_NODE) if const.PYRS_DIR_NODE in config else DEFAULT_PYRS_DIR
    pyrs_dir = pathlib.Path(pyrs_dir)

    exec_context = ExecutionContext()
    exec_context.pyrsonalizer_directory = pyrs_dir
    return exec_context
