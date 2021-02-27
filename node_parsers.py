import logging
from typing import Dict, Union
import pathlib

import const
import utils
import actions
import errors

logger = logging.Logger(__name__)

REQUIRED_FS_NODES = {
    "local": ["file_path", "destination", "key"],
}

LOCATION_TYPES = [const.LOCATION_TYPE_LOCAL]


def parse_file_sync(
    file_sync_config: Dict[str, Union[str, bool, int]]
) -> actions.FileSync:
    if (
        const.LOCATION_TYPE_NODE not in file_sync_config
        or file_sync_config[const.LOCATION_TYPE_NODE] not in LOCATION_TYPES
    ):
        utils.log_and_raise(
            logger.error,
            ValueError,
            f"File sync config missing {const.LOCATION_TYPE_NODE}",
            errors.NP_MISSING_LOCATION_TYPE,
        )

    dependency_keys = file_sync_config.get(const.DEPENDENCY, [])

    location_type = file_sync_config[const.LOCATION_TYPE_NODE]
    if any(node not in file_sync_config for node in REQUIRED_FS_NODES[location_type]):
        utils.log_and_raise(
            logger.error,
            ValueError,
            "File sync config missing some required elements",
            errors.NP_MISSING_FILE_SYNC_CONFIG,
        )

    backend = None
    if location_type == const.LOCATION_TYPE_LOCAL:
        backend = actions.FileSyncBackendType.local

    if backend == actions.FileSyncBackendType.local:
        return actions.FileSync(
            backend=backend,
            file_source=actions.LocalFileLocation(
                pathlib.Path(file_sync_config[const.SOURCE_FILE_PATH])
            ),
            local_path=pathlib.Path(file_sync_config[const.DEST_FILE_PATH]),
            overwrite=file_sync_config.get(const.OVERWRITE, False),
            key=file_sync_config[const.NODE_KEY],
            dependency_keys=dependency_keys,
        )
    else:
        raise NotImplementedError()
