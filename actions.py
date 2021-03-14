"""This module contains class definitions for classes pertaining to actions"""
from typing import List, TypeVar, Generic, Optional
from enum import Enum
import os
from abc import ABC
import abc
import pathlib
import logging
import shutil
from datetime import datetime, timezone
import subprocess

import git
import validators
import prompt_toolkit
from prompt_toolkit import validation

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


class ModifiedDateDecisionEnum(Enum):
    """User decisions when a local file is newer than a remote file."""

    stop_execution = 1
    skip_this_action = 2
    proceed_once = 3
    ignore_in_future = 4


class UserStoppedExecutionException(BaseException):
    """Exception raised when a user has stopped the execution."""

    pass


class FileLocation(ABC):
    """Represents the source of a file used in a file sync action."""

    modified_date_prompt_string = "The modified time of the local file is newer than the file you're attempting to download. What would you like to do?\n1. Stop this execution\n2. Skip this action once\n3. Proceed with this action once\n4. Ignore this error for the rest of this execution\n\nDecision: "

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

    @abc.abstractmethod
    def get_modified_date(self) -> datetime:
        """An abstract method to return the last modified date of the file location."""
        pass

    def compare_modified_date(
        self, file_path: pathlib.Path
    ) -> Optional[ModifiedDateDecisionEnum]:
        """Compare the modified date of the local file and this FileLocation.

        Args:
             file_path: The path of the local file.

        Returns:
            The decision the user makes as a ModifiedDateDecisionEnum or None if there
            is no need.
        """
        if self.get_modified_date() < utils.get_file_modified_date(file_path):
            # noinspection PyTypeChecker
            validator: validation.Validator = (
                validation.Validator.from_callable(
                    lambda x: x in [str(x.value) for x in ModifiedDateDecisionEnum],
                    error_message="Invalid choice.",
                    move_cursor_to_end=True,
                ),
            )

            choice = prompt_toolkit.prompt(
                message=self.modified_date_prompt_string, validator=validator
            )

            return ModifiedDateDecisionEnum(int(choice))

        return None


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
        self._repo: git.Repo = None
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
            self._repo = git.Repo.clone_from(self.repo_url, dir_to_save)
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

    def get_modified_date(self) -> datetime:
        """Get the modified date of the last commit to main."""
        if self._path is None:
            self._clone()
        return self._repo.head.commit.committed_datetime.astimezone(timezone.utc)

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
        super().__init__()
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

    def get_modified_date(self) -> datetime:
        """Return the modified date of the file at `self.path`."""
        return utils.get_file_modified_date(self.path)


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

    def __init__(
        self,
        check_command: str,
        key: str,
        install_command: Optional[str] = None,
        dependency_keys: Optional[List[str]] = None,
    ):
        super().__init__(key=key, dependency_keys=dependency_keys)
        self.install_command = install_command
        self.check_command = check_command
        # TODO: Consider allowing user interaction during install.

    def _is_installed(self) -> bool:
        return (
            subprocess.run([arg for arg in self.check_command.split(" ")]).returncode
            == 0
        )

    def _install(self) -> bool:
        if self.install_command is not None:
            return (
                subprocess.run([arg for arg in self.install_command.split(" ")]).returncode
                == 0
            )
        return True

    def execute(self, exec_context: Optional[ExecutionContext] = None):
        """See base class."""
        if self._is_installed():
            return

        if not self._install():
            utils.log_and_raise(
                logger.error,
                f"Failed to install Installation with key {self.key}",
                ActionFailureException,
                errors.AC_FAILED_TO_INSTALL,
            )

        if not self._is_installed():
            if self.install_command is not None:
                logger.warning(
                    f"Installation with key {self.key} failed install check after"
                    f"successful installation."
                )
                return
            utils.log_and_raise(
                logger.error,
                f"'Check-only' installation with key {self.key} is not installed.",
                ActionFailureException,
                errors.AC_CHECK_ONLY_INSTALLATION_NOT_INSTALLED
            )

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

    def _handle_modified_date(self, exec_context: ExecutionContext) -> bool:
        """Based on the ModifiedDateDecisionEnum returned by compare_modified date, take
           an action.

        Args:
            exec_context: The execution context

        Returns:
            True if the action should finish executing, False if not.
        """
        choice = self.file_source.compare_modified_date(self.dest_path)

        if choice is not None:
            if choice == ModifiedDateDecisionEnum.stop_execution:
                utils.log_and_raise(
                    logger.error,
                    f"User stopped execution at action with key {self.key}",
                    UserStoppedExecutionException,
                    errors.AC_USER_STOPPED_EXECUTION,
                )
            elif choice == ModifiedDateDecisionEnum.skip_this_action:
                logger.info(f"Skipped action with key {self.key}")
                return False
            elif choice == ModifiedDateDecisionEnum.proceed_once:
                pass
            elif choice == ModifiedDateDecisionEnum.ignore_in_future:
                exec_context.skip_modified_date_warning = True
                return True

        return True

    def execute(self, exec_context: ExecutionContext) -> None:
        """Attempts to copy the source file to the destination.

        Gets a source file from self.file_source, an example of the Adapter pattern.

        Returns:
            True of the execution was successful.

        Raises:
            ActionFailureException: An error occurred executing this action.
        """
        source_path = self.file_source.get_file_path()

        if pathlib.Path(self.dest_path).resolve().is_file():
            if not self.overwrite:
                utils.log_and_raise(
                    logger.error,
                    f"File exists at {self.dest_path} and overwrite is not set to true.",
                    ActionFailureException,
                )
            else:
                if not self._handle_modified_date(exec_context):
                    return

        shutil.copy(source_path, self.dest_path)
