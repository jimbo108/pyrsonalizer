from typing import List, TypeVar, Generic, Optional
from enum import Enum
import os
from abc import ABC
import abc
import pathlib
import logging
import shutil

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


class FileExistsException(BaseException):
    pass


class FileLocationInvalidException(BaseException):
    pass


class Dependency(Generic[T]):
    def __init__(self, value: T):
        self.value: T = value


class Action(ABC):
    def __init__(self, key: int, dependency_keys: List[int] = []):
        self.dependencies: List[Dependency] = []
        self.key: str = key
        self.dependency_keys: List[str] = dependency_keys

    @abc.abstractmethod
    def execute(self):
        raise NotImplementedError()

    def add_dependency(self, dependency: Dependency) -> None:
        self.dependencies.append(dependency)

    def __hash__(self):
        hash_string = f"{self.__class__.__name__}_{self.key}"
        return hash(hash_string)


class NullAction(Action):
    """Will use this class for the root of the execution tree."""
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
        key: int,
        backend: FileSyncBackendType,
        file_source: FileLocation,
        local_path: pathlib.Path,
        overwrite: bool,
        dependency_keys: List[str] = [],
    ):
        self.backend: FileSyncBackendType = backend
        self.file_source: FileLocation = file_source
        self.local_path: pathlib.Path = local_path
        self.overwrite: bool = overwrite
        super().__init__(key, dependency_keys=dependency_keys)

    def execute(self) -> bool:
        if not self.overwrite and self.local_path.resolve().is_file():
            return False

        if type(self.file_source) == LocalFileLocation:
            breakpoint()
            shutil.copy(self.file_source.path, self.local_path)
            return True
        else:
            raise NotImplementedError()

    def download(self) -> None:
        # TODO: Probably get rid of this
        file_content = self.file_source.get_file_content()
        if not self.overwrite and os.path.exists(self.local_path):
            raise FileExistsException()

        try:
            self.file_source.get_file_content()
        except FileLocationInvalidException as err:
            logger.error(err)
