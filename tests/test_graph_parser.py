from typing import Callable, Type, Optional
import pathlib

import pytest

import graph_parser
import errors
import actions
import const
import execution_graph
from execution_context import ExecutionContext


@pytest.fixture
def mock_path_exists_dne(mocker):
    mock = mocker.patch("graph_parser.os.path.exists")
    mock.return_value = False
    return mock


@pytest.fixture
def mock_path_exists_happy(mocker):
    mock = mocker.patch("graph_parser.os.path.exists")
    mock.return_value = True


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


@pytest.fixture
def mock_get_config_bad_klass(mocker):
    mock = mocker.patch("graph_parser._get_config")
    mock.return_value = {"bad_key": {}}


@pytest.fixture
def mock_get_config_bad_deps(mocker):
    mock = mocker.patch("graph_parser._get_config")
    mock.return_value = {
        "file_syncs": [
            {
                const.LOCATION_TYPE_NODE: const.LOCATION_TYPE_LOCAL,
                const.SOURCE_FILE_PATH: "source_path",
                const.DEST_FILE_PATH: "dest_path",
                const.NODE_KEY: "key_one",
                const.DEPENDENCY: ["key_three"],
            },
            {
                const.LOCATION_TYPE_NODE: const.LOCATION_TYPE_LOCAL,
                const.SOURCE_FILE_PATH: "source_path",
                const.DEST_FILE_PATH: "dest_path",
                const.NODE_KEY: "key_two",
            },
        ]
    }


@pytest.fixture
def mock_get_config_happy_deps_github(mocker):
    mock = mocker.patch("graph_parser._get_config")
    mock.return_value = {
        "file_syncs": [
            {
                const.LOCATION_TYPE_NODE: const.LOCATION_TYPE_GITHUB,
                const.SOURCE_FILE_PATH: "source_path",
                const.REPOSITORY: "http://testsite.com/uname/projname",
                const.DEST_FILE_PATH: "dest_path",
                const.NODE_KEY: "key_one",
                const.DEPENDENCY: ["key_two"],
            },
            {
                const.LOCATION_TYPE_NODE: const.LOCATION_TYPE_GITHUB,
                const.SOURCE_FILE_PATH: "source_path",
                const.REPOSITORY: "http://testsite.com/uname/projname",
                const.DEST_FILE_PATH: "dest_path",
                const.NODE_KEY: "key_two",
            },
        ]
    }


@pytest.fixture
def mock_get_config_happy_deps_local(mocker):
    mock = mocker.patch("graph_parser._get_config")
    mock.return_value = {
        "file_syncs": [
            {
                const.LOCATION_TYPE_NODE: const.LOCATION_TYPE_LOCAL,
                const.SOURCE_FILE_PATH: "source_path",
                const.DEST_FILE_PATH: "dest_path",
                const.NODE_KEY: "key_one",
                const.DEPENDENCY: ["key_two"],
            },
            {
                const.LOCATION_TYPE_NODE: const.LOCATION_TYPE_LOCAL,
                const.SOURCE_FILE_PATH: "source_path",
                const.DEST_FILE_PATH: "dest_path",
                const.NODE_KEY: "key_two",
            },
        ]
    }


@pytest.fixture
def mock_get_config_happy(mocker):
    mock = mocker.patch("graph_parser._get_config")
    mock.return_value = {
        "file_syncs": [
            {
                const.LOCATION_TYPE_NODE: const.LOCATION_TYPE_LOCAL,
                const.SOURCE_FILE_PATH: "source_path",
                const.DEST_FILE_PATH: "dest_path",
                const.NODE_KEY: "key_two",
            }
        ]
    }


class TestGraphParser:
    exec_context = ExecutionContext(pyrsonalizer_directory="./test_app_dir")

    def test_path_does_not_exist__raises(self, mock_log_and_raise):
        test_path = "path"
        with pytest.raises(ValueError):
            graph_parser.parse_execution_graph(pathlib.Path(test_path), self.exec_context)

        call_args = mock_log_and_raise.call_args[0]
        assert errors.GP_PATH_DOES_NOT_EXIST in call_args

    def test_no_class_mapping__raises(
        self, mock_log_and_raise, mock_get_config_bad_klass
    ):
        test_path = "path"
        with pytest.raises(ValueError):
            graph_parser.parse_execution_graph(pathlib.Path(test_path), self.exec_context)

        call_args = mock_log_and_raise.call_args[0]
        assert errors.GP_NO_CLASS_MAP in call_args

    def test_bad_dependency_ref__raises(
        self, mock_log_and_raise, mock_get_config_bad_deps
    ):
        test_path = "path"
        with pytest.raises(KeyError):
            graph_parser.parse_execution_graph(pathlib.Path(test_path), self.exec_context)

        call_args = mock_log_and_raise.call_args[0]
        assert errors.GP_BAD_DEPENDENCY_REF in call_args

    def test_happy_path(self, mock_get_config_happy):
        result_graph = None
        try:
            result_graph = graph_parser.parse_execution_graph(pathlib.Path("test_path"), self.exec_context)
        except BaseException as err:
            pytest.fail()

        assert isinstance(result_graph._root, execution_graph.GraphNode)
        children = result_graph._root.children
        assert len(children) == 1
        child = children[0]

        assert child.value.backend == actions.FileSyncBackendType.local
        assert str(child.value.file_source.path) == "source_path"
        assert str(child.value.dest_path) == "dest_path"
        assert child.value.overwrite is False

    def test_happy_path_with_deps(self, mock_get_config_happy_deps_local):
        result_graph = None
        try:
            result_graph = graph_parser.parse_execution_graph(pathlib.Path("test_path"), self.exec_context)
        except BaseException as err:
            pytest.fail()

        assert isinstance(result_graph._root, execution_graph.GraphNode)
        children = result_graph._root.children
        assert len(children) == 1
        child = children[0]

        assert child.value.backend == actions.FileSyncBackendType.local
        assert str(child.value.file_source.path) == "source_path"
        assert str(child.value.dest_path) == "dest_path"
        assert child.value.overwrite is False
        assert child.value.key == "key_one"

        grandchild = child.children[0]

        assert grandchild.value.backend == actions.FileSyncBackendType.local
        assert str(grandchild.value.file_source.path) == "source_path"
        assert str(grandchild.value.dest_path) == "dest_path"
        assert grandchild.value.overwrite is False
        assert grandchild.value.key == "key_two"
