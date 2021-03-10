import os
from unittest import mock
import pathlib

import e2e_utils
from main import main as prog_main

TEST_FILE_ONE = "test_file_1.txt"
TEST_FILE_TWO = "test_file_2.txt"

class EndToEndTestException(BaseException):
    pass


@e2e_utils.e2e_test
def test_happy_path_local():
    args = ["--path", "./test-configs/local_file_sync.yml"]
    prog_main(args)

    assert os.path.exists(os.path.join(e2e_utils.TEST_DEST_DIR, TEST_FILE_ONE))
    assert os.path.exists(os.path.join(e2e_utils.TEST_DEST_DIR, TEST_FILE_TWO))


@e2e_utils.e2e_test
def test_happy_path_github():
    args = ["--path", "./test-configs/github_file_sync.yml"]
    prog_main(args)

    assert os.path.exists(os.path.join(e2e_utils.TEST_DEST_DIR, TEST_FILE_ONE))
    assert os.path.exists(os.path.join(e2e_utils.TEST_DEST_DIR, TEST_FILE_TWO))
    assert os.path.exists(os.path.join(e2e_utils.TEST_DEST_DIR, e2e_utils.VIMRC))


@e2e_utils.e2e_test
def test_failed_dependency__does_not_proceed():
    args = ["--path", "./test-configs/local_file_sync__bad_dep.yml"]
    try:
        prog_main(args)
    except EnvironmentError:
        assert not os.path.exists(os.path.join(e2e_utils.TEST_DEST_DIR, TEST_FILE_ONE))
        assert not os.path.exists(os.path.join(e2e_utils.TEST_DEST_DIR, TEST_FILE_TWO))
        return

    raise EndToEndTestException(f"Environment error expected in test_failed_dependency__does_not_proceed but did not occur.")


@e2e_utils.e2e_test
def test_github_file_sync_existing_file__prompts():
    args = ["--path", "./test-configs/github_file_sync__existing_file.yml"]
    open(os.path.join(e2e_utils.TEST_DEST_DIR, ".vimrc"), 'a').close()

    with mock.patch("actions.prompt_toolkit.prompt") as mocked:
        mocked.return_value = "2"
        prog_main(args)

    assert os.path.exists(os.path.join(e2e_utils.TEST_DEST_DIR, TEST_FILE_ONE))
    assert os.path.exists(os.path.join(e2e_utils.TEST_DEST_DIR, TEST_FILE_TWO))

    path = pathlib.Path(os.path.join(e2e_utils.TEST_DEST_DIR, ".vimrc"))

    assert path.exists()
    assert path.stat().st_size == 0


if __name__ == '__main__':
    test_happy_path_local()
    test_happy_path_github()
    test_failed_dependency__does_not_proceed()
    test_github_file_sync_existing_file__prompts()
