from typing import Callable, Type, Optional
import pathlib

import pytest

import node_parsers
import errors
import actions
import const
from tests import test_utils


def mock_log_and_raise_func(
    logger_func: Callable,
    exception: Type[BaseException],
    error_message: str,
    error_key: Optional[str] = None,
):
    raise exception


@pytest.fixture(autouse=True)
def mock_log_and_raise(mocker):
    mock = mocker.patch(
        "node_parsers.utils.log_and_raise",
    )
    mock.side_effect = mock_log_and_raise_func

    return mock


class TestParseFileSync:
    def test_no_location_node__log_and_raise(self, mock_log_and_raise):
        test_file_sync_config = {}
        with pytest.raises(ValueError):
            node_parsers.parse_file_sync(test_file_sync_config)
        call_args = mock_log_and_raise.call_args[0]
        assert errors.NP_MISSING_LOCATION_TYPE in call_args

    def test_local_missing_required__log_and_raise(self, mock_log_and_raise):
        test_file_sync_config = {
            const.LOCATION_TYPE_NODE: const.LOCATION_TYPE_LOCAL,
            const.DEST_FILE_PATH: "file_path",
        }
        with pytest.raises(ValueError):
            node_parsers.parse_file_sync(test_file_sync_config)
        call_args = mock_log_and_raise.call_args[0]
        assert errors.NP_MISSING_FILE_SYNC_CONFIG in call_args

    def test_happy_path__file_sync_created(self):
        test_source_path = "test_source_path"
        test_dest_path = "test_dest_path"
        test_key = "test_key"
        test_dep_keys = ["test_dep_key_one", "test_dep_key_two"]

        test_file_sync_config = {
            const.LOCATION_TYPE_NODE: const.LOCATION_TYPE_LOCAL,
            const.SOURCE_FILE_PATH: test_source_path,
            const.DEST_FILE_PATH: test_dest_path,
            const.NODE_KEY: test_key,
            const.DEPENDENCY: test_dep_keys,
        }
        file_sync = node_parsers.parse_file_sync(test_file_sync_config)

        expected_file_sync = actions.FileSync(
            backend=actions.FileSyncBackendType.local,
            file_source=actions.LocalFileLocation(pathlib.Path(test_source_path)),
            local_path=pathlib.Path(test_dest_path),
            overwrite=False,
            key=test_key,
            dependency_keys=test_dep_keys,
        )
        assert test_utils.naive_object_comparison(file_sync, expected_file_sync)

    def test_unsupported_backend__raises(self):
        pass
