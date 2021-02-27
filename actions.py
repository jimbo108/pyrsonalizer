from typing import List, TypeVar, Generic, Optional
from enum import Enum
import os
from abc import ABC
import abc
import pathlib
import logging
import shutil

import utils

import const

logger = logging.Logger(__file__)

LOG_MSG_PROBLEM_GETING_SOURCE_FILE = f"There was a problem"

T = TypeVar("T")


class FileSyncBackendType(Enum):
    github = "github"
    pyrsonalizer_server = "pyrsonalizer_server"
    local = "local"


class FileLocation(ABC):
    @abc.abstractmethod
    def get_file_content(self) -> str:
        pass


class LocalFileLocation(FileLocation):
    def __init__(self, path: pathlib.Path):
        self.path = path

    def get_file_content(self) -> str:
        with open(self.path) as fh:
            return fh.read()

    def __eq__(self, other) -> bool:
        return self.path == other.path


class FileExistsException(BaseException):
    pass


class FileLocationInvalidException(BaseException):
    pass


class Dependency(Generic[T]):
    def __init__(self, value: T):
        self.value: T = value


class ActionFailureException(BaseException):
    pass


class Action(ABC):
    def __init__(self, key: str, dependency_keys: Optional[List[str]] = None):
        self.dependencies: List[Dependency] = []
        self.key: str = key
        self.dependency_keys: List[str] = (
            dependency_keys if dependency_keys is not None else []
        )

    @abc.abstractmethod
    def execute(self):
        raise NotImplementedError()

    def add_dependency(self, dependency: Dependency) -> None:
        self.dependencies.append(dependency)

    def __hash__(self):
        hash_string = f"{self.__class__.__name__}_{self.key}"
        return hash(hash_string)


class NullAction(Action):
    """Will use this class for the root of the execution graph."""
    def execute(self):
        return True


class Installation(Action):
    def execute(self):
        raise NotImplementedError()


class EnvironmentCondition(object):
    pass


class FileSync(Action):
    def __init__(
        self,
        key: str,
        backend: FileSyncBackendType,
        file_source: FileLocation,
        local_path: pathlib.Path,
        overwrite: bool,
        dependency_keys: Optional[List[str]] = None,
    ):
        self.backend: FileSyncBackendType = backend
        self.file_source: FileLocation = file_source
        self.local_path: pathlib.Path = local_path
        self.overwrite: bool = overwrite
        super().__init__(key, dependency_keys=dependency_keys)

    def execute(self) -> bool:
        if not self.overwrite and self.local_path.resolve().is_file():
            utils.log_and_raise(
                logger.error,
                ActionFailureException,
                f"File exists at {self.local_path} and overwrite is not set to true.",
            )

        if type(self.file_source) == LocalFileLocation:
            shutil.copy(self.file_source.path, self.local_path)
            return True
        else:
            raise NotImplementedError()
