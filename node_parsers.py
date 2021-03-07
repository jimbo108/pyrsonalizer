"""Contains parsing functions or classes for each type of node in the execution tree.

This exists separately from the __init__ methods of those nodes in order to decouple
changes to the input file from the classes themselves.
"""
import logging
from typing import Dict, Union, Optional
import pathlib

import const
import utils
import actions
import errors
from execution_context import ExecutionContext

logger = logging.Logger(__name__)

REQUIRED_FS_NODES = {
    actions.FileSyncBackendType.local: [
        const.SOURCE_FILE_PATH,
        const.DEST_FILE_PATH,
        const.NODE_KEY,
    ],
    actions.FileSyncBackendType.github: [
        const.REPOSITORY,
        const.SOURCE_FILE_PATH,
        const.DEST_FILE_PATH,
        const.NODE_KEY,
    ],
}

LOCATION_TYPES = [const.LOCATION_TYPE_LOCAL, const.LOCATION_TYPE_GITHUB]


def map_location_type(location_type: str) -> actions.FileSyncBackendType:
    if location_type == const.LOCATION_TYPE_LOCAL:
        return actions.FileSyncBackendType.local
    elif location_type == const.LOCATION_TYPE_GITHUB:
        return actions.FileSyncBackendType.github
    else:
        utils.log_and_raise(
            logger.error,
            f"Invalid location_type {location_type}.",
            NotImplementedError,
            errors.NP_INVALID_LOCATION_TYPE,
        )


def parse_file_sync(
    file_sync_config: Dict[str, Union[str, bool, int]], exec_context: Optional[ExecutionContext] = None
) -> actions.FileSync:
    """Creates an Action object from configuration."""
    if (
        const.LOCATION_TYPE_NODE not in file_sync_config
        or file_sync_config[const.LOCATION_TYPE_NODE] not in LOCATION_TYPES
    ):
        utils.log_and_raise(
            logger.error,
            f"File sync config missing {const.LOCATION_TYPE_NODE}",
            ValueError,
            errors.NP_MISSING_LOCATION_TYPE,
        )
    if exec_context is None and file_sync_config[const.LOCATION_TYPE_NODE] == const.LOCATION_TYPE_GITHUB:
        utils.log_and_raise(
            logger.error,
            f"Execution contet must be passed in when file sync is of type {const.LOCATION_TYPE_GITHUB}.",
            ValueError,
            errors.NP_MISSING_EXEC_CONTEXT
        )

    dependency_keys = file_sync_config.get(const.DEPENDENCY, [])

    backend = map_location_type(file_sync_config[const.LOCATION_TYPE_NODE])

    if any(node not in file_sync_config for node in REQUIRED_FS_NODES[backend]):
        utils.log_and_raise(
            logger.error,
            "File sync config missing some required elements",
            ValueError,
            errors.NP_MISSING_FILE_SYNC_CONFIG,
        )

    file_source = None
    if backend == actions.FileSyncBackendType.local:
        file_source = actions.LocalFileLocation(
            pathlib.Path(file_sync_config[const.SOURCE_FILE_PATH])
        )
    elif backend == actions.FileSyncBackendType.github:
        file_source = actions.GithubFileLocation(
            file_sync_config[const.REPOSITORY],
            pathlib.PurePath(file_sync_config[const.SOURCE_FILE_PATH]),
            exec_context.pyrsonalizer_directory,
        )

    return actions.FileSync(
        backend=backend,
        file_source=file_source,
        local_path=pathlib.Path(file_sync_config[const.DEST_FILE_PATH]),
        overwrite=file_sync_config.get(const.OVERWRITE, False),
        key=file_sync_config[const.NODE_KEY],
        dependency_keys=dependency_keys,
    )
