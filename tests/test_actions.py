from typing import Callable, Type, Optional
import pathlib
import os

import pytest
import git

import actions
import errors


def mock_log_and_raise_func(
    logger_func: Callable,
    error_message: str,
    exception: Type[BaseException],
    error_key: Optional[str] = None,
):
    raise exception


@pytest.fixture(autouse=True)
def mock_log_and_raise(mocker):
    mock = mocker.patch(
        "graph_parser.utils.log_and_raise",
    )
    mock.side_effect = mock_log_and_raise_func

    return mock


@pytest.fixture(autouse=True)
def mock_pathlib_path_happy(mocker):
    mock = mocker.patch("actions.pathlib.Path")
    return mock


@pytest.fixture
def mock_git_repo_happy(mocker):
    mock = mocker.patch("actions.git.Repo.clone_from")
    return mock


@pytest.fixture
def mock_git_repo_raises(mocker):
    mock = mocker.patch("actions.git.Repo.clone_from")
    mock.side_effect = git.exc.GitCommandError("cmd", "status")
    return mock

@pytest.fixture
def mock_is_file_invalid(mocker):
    mock = mocker.patch("actions.pathlib.Path")
    mock.return_value.resolve.return_value.is_file.return_value = False
    return mock

@pytest.fixture
def mock_is_file_happy(mocker):
    mock = mocker.patch("actions.pathlib.Path")
    mock.return_value.resolve.return_value.is_file.return_value = True
    return mock

class TestGithubFileLocation:
    def test_invalid_url__raises(
        self,
        mock_git_repo_happy,
        mock_log_and_raise,
    ):
        test_user = "test_user"
        test_repo_name = "test_repo_name"
        source_file_path = "test_file"
        test_app_dir = "test_app_dir"
        test_repo_url = f"bad_url/{test_user}{test_repo_name}"
        with pytest.raises(ValueError):
            github_file_location = actions.GithubFileLocation(
                repo_url=test_repo_url,
                relative_path=pathlib.PurePath(source_file_path),
                app_dir=test_app_dir,
            )

        call_args = mock_log_and_raise.call_args[0]
        assert errors.AC_BAD_GITHUB_URL in call_args

    def test_problem_cloning__raises(self, mock_git_repo_raises, mock_log_and_raise):
        test_user = "test_user"
        test_repo_name = "test_repo_name"
        source_file_path = "test_file"
        test_app_dir = "test_app_dir"
        test_repo_url = f"http://www.fake-repo.com/{test_user}/{test_repo_name}"
        github_file_location = actions.GithubFileLocation(
            repo_url=test_repo_url,
            relative_path=pathlib.PurePath(source_file_path),
            app_dir=test_app_dir,
        )
        with pytest.raises(git.exc.GitCommandError):
            github_file_location.get_file_path()

        call_args = mock_log_and_raise.call_args[0]
        assert errors.AC_FAILED_TO_CLONE in call_args

    def test_file_does_not_exist_in_repo__raises(
        self,
        mock_is_file_invalid,
        mock_git_repo_happy,
        mock_log_and_raise,
    ):
        test_user = "test_user"
        test_repo_name = "test_repo_name"
        source_file_path = "test_file"
        test_app_dir = "test_app_dir"
        test_repo_url = f"http://www.fake-repo.com/{test_user}/{test_repo_name}"
        github_file_location = actions.GithubFileLocation(
            repo_url=test_repo_url,
            relative_path=pathlib.PurePath(source_file_path),
            app_dir=test_app_dir,
        )
        with pytest.raises(ValueError):
            github_file_location.get_file_path()

        call_args = mock_log_and_raise.call_args[0]
        assert errors.AC_BAD_FINAL_FILE_PATH in call_args

    def test_happy_path(self, mock_git_repo_happy, mock_is_file_happy):
        test_user = "test_user"
        test_repo_name = "test_repo_name"
        source_file_path = "test_file"
        test_app_dir = "test_app_dir"
        test_repo_url = f"http://www.fake-repo.com/{test_user}/{test_repo_name}"
        github_file_location = actions.GithubFileLocation(
            repo_url=test_repo_url,
            relative_path=pathlib.PurePath(source_file_path),
            app_dir=test_app_dir,
        )

        github_file_location.get_file_path()
        result_path = github_file_location._path

        assert result_path == os.path.join(
            test_app_dir, test_user + "." + test_repo_name, source_file_path
        )
