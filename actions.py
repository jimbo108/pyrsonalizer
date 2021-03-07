"""This module contains class definitions for classes pertaining to actions"""
from typing import List, TypeVar, Generic, Optional
from enum import Enum
import os
from abc import ABC
import abc
import pathlib
import logging
import shutil

import git
import validators

import utils
from execution_context import ExecutionContext
import const
import errors

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

    @abc.abstractmethod
    def get_file_path(self) -> pathlib.Path:
        """An abstract method intended to return the path of a file with the content
        from this file source.

        In some cases this will be content copied to a temp file.
        """
        pass


class GithubFileLocation(FileLocation):
    """This class is resposible for downloading a file from Github and putting it
        somewhere.

    It downloads the content lazily, when get_file_path is actually called by the
    parser.

    Attributes:
        repo_url: The URL of the respository that we are downloading the file from.
        relative_path: The path of the relevant file relative to the Github repo.
    """
    def __init__(
        self, repo_url: str, relative_path: pathlib.PurePath, app_dir: pathlib.Path
    ):
        super().__init__()
        self._path: Optional[pathlib.Path] = None
        self.repo_url = repo_url
        self._set_repo_name()

        self.relative_path = relative_path
        self._app_dir = app_dir

    def _set_repo_name(self) -> None:
        if not validators.url(self.repo_url):
            utils.log_and_raise(
                logger.error,
                f"Invalid URL {self.repo_url}.",
                ValueError,
                errors.AC_BAD_GITHUB_URL,
            )
        self._repo_name = ".".join(self.repo_url.split("/")[-2:])

    def _clone(self) -> None:
        try:
            dir_to_save = os.path.join(self._app_dir, self._repo_name)
            try:
                shutil.rmtree(dir_to_save)
            except FileNotFoundError:
                pass
            git.Repo.clone_from(self.repo_url, dir_to_save)
            self._path = os.path.join(dir_to_save, self.relative_path)
        except git.exc.GitCommandError as err:
            utils.log_and_raise(
                logger.error,
                f"There was a problem downloading from the git repo at {self.repo_url} to {self._app_dir}",
                err,
                errors.AC_FAILED_TO_CLONE,
            )

        if not pathlib.Path(self._path).resolve().is_file():
            utils.log_and_raise(
                logger.error,
                f"Github file to sync at path {self._path} does not exist.",
                ValueError,
                errors.AC_BAD_FINAL_FILE_PATH,
            )

    def get_file_path(self) -> pathlib.Path:
        """Clones the repository and then returns the location of the relevant file."""
        if self._path is None:
            self._clone()
        return pathlib.Path(self._path)

    def get_file_content(self) -> str:
        raise NotImplementedError()

    def __eq__(self, other):
        """Used for testing."""
        return (
            (self._path == other.path)
            and (self.repo_url == other.repo_url)
            and (self._repo_name == other._repo_name)
            and (self.relative_path == other.relative_path)
            and (self._app_dir == other._app_dir)
        )


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

    def get_file_path(self) -> pathlib.Path:
        if not os.path.exists(self.path):
            raise EnvironmentError(f"{self.path} does not exist.")
        return self.path

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
        overwrite: Whether or not a local file at self.dest_path should be overwritten
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
        self.dest_path: pathlib.Path = local_path
        self.overwrite: bool = overwrite

    def execute(self, exec_context: ExecutionContext) -> None:
        """Attempts to copy the source file to the destination.

        Gets a source file from self.file_source, an example of the Adapter pattern.

        Returns:
            True of the execution was successful.

        Raises:
            ActionFailureException: An error occurred executing this action.
        """
        source_path = self.file_source.get_file_path()
        full_dest_path = os.path.join(self.dest_path, source_path.name)

        if not self.overwrite and pathlib.Path(full_dest_path).resolve().is_file():
            utils.log_and_raise(
                logger.error,
                f"File exists at {self.dest_path} and overwrite is not set to true.",
                ActionFailureException,
            )

        shutil.copy(source_path, self.dest_path)
