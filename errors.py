"""Stores error keys to identify unique errors.

This is intended to:
    1. Make unit testing easier by avoiding formatted string comparisons.
    2. Make a transition to to some metric framework easier.

NP = node_parsers
GP = graph_parser
EG = execution_graph
"""

# Error Keys
NP_MISSING_LOCATION_TYPE = "missing_location_type"
NP_MISSING_FILE_SYNC_CONFIG = "missing_file_sync_config"
GP_PATH_DOES_NOT_EXIST = "gp_path_does_not_exist"
GP_NO_CLASS_MAP = "gp_no_class_map"
GP_NO_PARSER_FUNC_MAP = "gp_no_parser_func_map"
GP_BAD_DEPENDENCY_REF = "gp_bad_dependency_ref"
EG_CIRCULAR_DEPENDENCY = "eg_circular_dependency"
EG_IMPOSSIBLE_STATE = "eg_impossible_state"


class ImpossibleStateException(BaseException):
    """Represents an impossible state occurring due to a programming error or unforeseen input."""

    pass
