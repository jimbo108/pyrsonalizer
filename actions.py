"""This module contains class definitions for classes pertaining to actions"""
from typing import List, TypeVar, Generic, Optional
from enum import Enum
import os
from abc import ABC
import abc
import pathlib
import logging
import shutil

import utils
from execution_context import ExecutionContext
import const

logger = logging.Logger(__file__)

LOG_MSG_PROBLEM_GETING_SOURCE_FILE = f"There was a problem"

T = TypeVar("T")


class FileSyncBackendType(Enum):
    """Enum for representing the type of backend a file sync action uses."""

    github = "github"
    pyrsonalizer_server = "pyrsonalizer_server"
    local = "local"


class FileLocation(ABC):
    """Represents the source of a file used in a file sync action."""

    @abc.abstractmethod
    def get_file_content(self) -> str:
        """An abstract method intended to return file content for all child classes."""
        pass


class LocalFileLocation(FileLocation):
    """Child class of file location representing a local file source.

    Attributes:
         path: The file as an absolute path.
    """

    def __init__(self, path: pathlib.Path):
        self.path = path

    def get_file_content(self) -> str:
        """See base class."""
        with open(self.path) as fh:
            return fh.read()

    def __eq__(self, other) -> bool:
        return self.path == other.path


class FileExistsException(BaseException):
    """An exception representing a FileLocatino that doesn not exist."""

    pass


class Dependency(Generic[T]):
    """A thin wrapper around some value meant to represent an action dependency.

    Attributes:
         value: The (generally object) that is depended on, generally an Action.
    """

    def __init__(self, value: T):
        self.value: T = value


class ActionFailureException(BaseException):
    """An exception raised when an Action.execute fails."""

    pass


class Action(ABC):
    """Represents some action that the user has configured the script to take.

    Currently, an action represents a file sync or an installation.

    Attributes:
        dependencies: Pointers to other actions that must successfully execute for this action to attempt to execute
        key: The key representing the action. Specified by the user in the configuration file.
        dependency_keys: Pointers to other action keys, used to poplate dependencies

    """

    def __init__(self, key: str, dependency_keys: Optional[List[str]] = None):
        self.dependencies: List[Dependency] = []
        self.key: str = key
        self.dependency_keys: List[str] = (
            dependency_keys if dependency_keys is not None else []
        )

    @abc.abstractmethod
    def execute(self, exec_context: ExecutionContext):
        """Run the action."""
        raise NotImplementedError()

    def add_dependency(self, dependency: Dependency) -> None:
        """Add a dependency to self.dependencies."""
        self.dependencies.append(dependency)

    def __hash__(self):
        """Hashes the object using key and class.

        This dunder was overridden to allow actions to be mapped to GraphNodes.

        Returns:
            A hash string to be used by dictionaries.
        """
        hash_string = f"{self.__class__.__name__}_{self.key}"
        return hash(hash_string)


class NullAction(Action):
    """Will use this class for the root of the execution graph."""

    def execute(self, exec_context: ExecutionContext):
        """This action is not intended to do anything."""
        return True


class Installation(Action):
    """An action that installs software.

    TODO: Implement
    """

    def execute(self, exec_context: ExecutionContext):
        """See base class."""
        raise NotImplementedError()


class EnvironmentCondition(object):
    """An condition of the environment specified by the user that is required for actions in this exection graph to run
    successfully."""

    pass


class FileSync(Action):
    """Represents an action that syncs files from one place to another.

    Will likely be subclassed at some point when nonlocal file syncs are supported.

    Attributes:
        key: See base class.
        backend: The type of source for the file being synced. Currently only local is supported.
        file_source: An object representing the location of a source file.
        local_path: The local path where the file should be stored.
        overwrite: Whether or not a local file at self.local_path should be overwritten
        dependency_keys: See base class.
    """

    def __init__(
        self,
        key: str,
        backend: FileSyncBackendType,
        file_source: FileLocation,
        local_path: pathlib.Path,
        overwrite: bool,
        dependency_keys: Optional[List[str]] = None,
    ):
        super().__init__(key, dependency_keys=dependency_keys)
        self.backend: FileSyncBackendType = backend
        self.file_source: FileLocation = file_source
        self.local_path: pathlib.Path = local_path
        self.overwrite: bool = overwrite

    def execute(self, exec_context: ExecutionContext) -> bool:
        """Attempts to copy the source file to the destination.

        Currently assumes a local file source. Will need to be changed later TODO.

        Returns:
            True of the execution was successful.

        Raises:
            ActionFailureException: An error occurred executing this action.
        """
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
