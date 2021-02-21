from enum import Enum
import os
from abc import ABC
import abc
import pathlib
import logging

logger = logging.Logger(__file__)

LOG_MSG_PROBLEM_GETING_SOURCE_FILE = f"There was a problem"


class FileSyncBackendType(Enum):
    github = 1
    pyrsonalizer_server = 2
    local = 3


class FileLocation(ABC):
    @abc.abstractmethod
    def get_file_content(self) -> str:
        pass


class FileExistsException(BaseException):
    pass


class FileLocationInvalidException(BaseException):
    pass


class Action(ABC):

    @abc.abstractmethod
    def execute(self):
        pass


class Installation(Action):
    pass


class FileSync(Action):
    def __init__(
        self,
        backend: FileSyncBackendType,
        file_source: FileLocation,
        local_path: pathlib.PurePath,
        overwrite: bool,
    ):
        self.backend: FileSyncBackendType = backend
        self.file_source: FileLocation = file_source
        self.local_path: pathlib.PurePath = local_path
        self.overwrite: bool = overwrite

    def download(self) -> None:
        file_content = self.file_source.get_file_content()
        if not self.overwrite and os.path.exists(self.local_path):
            raise FileExistsException()

        try:
            self.file_source.get_file_content()
        except FileLocationInvalidException as err:
            logger.error(err)
