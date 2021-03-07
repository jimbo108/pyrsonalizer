from typing import Callable
import os
from distutils import dir_util
import shutil

TEST_DIR = "./test-directory"
TEST_FILES_DIR = "./test-files"
TEST_SOURCE_DIR = "test-directory/test_inner_directory_src"
TEST_DEST_DIR = "test-directory/test_inner_directory_dest"
VIMRC = ".vimrc"


def setup():
    try:
        shutil.rmtree(TEST_DIR)
    except OSError as err:
        pass
    os.mkdir(TEST_DIR)
    os.mkdir(TEST_SOURCE_DIR)
    os.mkdir(TEST_DEST_DIR)

    dir_util.copy_tree(TEST_FILES_DIR, TEST_SOURCE_DIR)


def teardown():
    shutil.rmtree(TEST_DIR)


def e2e_test(func: Callable) -> None:
    def inner_func():
        setup()
        try:
            func()
        except BaseException as err:
            print(f"Failed test with error {err}.")
            raise err
        finally:
            teardown()

        print(f"{func.__name__} was successful\n")

    return inner_func
