"""This module contains functions to parse an ExecutionGraph class from the user input
configuration."""

from typing import Any, Type, Union, Set, List, Dict, Callable
import yaml
import pathlib
import os
import logging
from dataclasses import dataclass, field
import uuid

import utils
import actions
from execution_graph import ExecutionGraph, GraphNode
from actions import Action
import node_parsers
import errors

logger = logging.Logger(__file__)

KLASS_MAP = {
    "file_syncs": actions.FileSync,
    "installation": actions.Installation,
    "environment_condition": actions.EnvironmentCondition,
}

PARSER_MAP: Dict[Type, Callable] = {actions.FileSync: node_parsers.parse_file_sync}


@dataclass
class ParserState:
    """Maintains state for parsing the execution graph.

    ParserState is a container created for convenience, to tie the parser state together
    in one place and avoid excessive parameter passing.

    Attributes:
         action_list: The list of all actions in no particular order.
         key_object_mapping: Maps an action's `key` to the action itself.
         object_node_mapping: Maps an Action object to the GraphNode that contains it.
         condition_list: The list of all environment conditions in no particular order.
    """

    action_list: List[Action] = field(default_factory=lambda: [])
    key_object_mapping: Dict[str, object] = field(default_factory=lambda: {})
    object_node_mapping: Dict[Action, GraphNode[Action]] = field(
        default_factory=lambda: {}
    )
    condition_list: List[actions.EnvironmentCondition] = field(
        default_factory=lambda: []
    )


def _handle_add_action(action: Action, parser_state: ParserState) -> None:
    parser_state.action_list.append(action)
    parser_state.key_object_mapping[action.key] = action
    node = GraphNode(value=action)
    parser_state.object_node_mapping[action] = node


def _get_klass_for_node(node: str) -> Type:
    """Gets the class associated with a top-level configuration node like "file_syncs"."""
    klass = KLASS_MAP.get(node, None)
    if klass is None:
        utils.log_and_raise(
            logger.error,
            ValueError,
            f"Couldn't map yaml node {node} to a class.",
            errors.GP_NO_CLASS_MAP,
        )
    return klass


def _get_func_for_klass(klass: Type) -> Callable:
    """Gets the parser function for a given class `klass`.

    This strategy intends to better encapsulate changes to the input file format,
    avoiding changes to the underlying action class's __init__ as a result.

    Args:
        klass: The class to map

    Returns:
        A parser function that returns an instance of `klass`.
    """
    klass = PARSER_MAP.get(klass, None)
    if klass is None:
        utils.log_and_raise(
            logger.error,
            ValueError,
            f"Couldn't map class {klass} to parser function",
            errors.GP_NO_PARSER_FUNC_MAP,
        )
    return klass


def _get_config(path: Union[pathlib.Path, os.PathLike]) -> Dict[str, Any]:
    if not os.path.exists(path):
        utils.log_and_raise(
            logger.error,
            ValueError,
            f"Path {str(path)} does not exist.",
            errors.GP_PATH_DOES_NOT_EXIST,
        )

    with open(path) as fh:
        return yaml.load(fh, Loader=yaml.BaseLoader)


def _parse_objects(
    config: Dict[str, Any],
) -> ParserState:
    """Iterates over the input configuration and creates objects.

    This function is not responsible for tying these objecs together in any way.

    Args:
        config: The input config.

    Returns:
        A ParserState object containing additioanl actions and conditions.
    """
    parser_state = ParserState()
    for key in config.keys():
        klass = _get_klass_for_node(key)
        parser_func = _get_func_for_klass(klass)

        for obj_config in config[key]:
            instance = parser_func(obj_config)
            if issubclass(klass, Action):
                _handle_add_action(instance, parser_state)

            elif issubclass(klass, actions.EnvironmentCondition):
                parser_state.condition_list.append(instance)

    return parser_state


def _build_dependency_graph(
    action_list: List[Action], object_mapping: Dict[str, object]
) -> None:
    """Builds the Dependency objects from Action.dependency_keys for each action.

    Args:
        action_list: The list of all actions.
        object_mapping: Mapping from action.key to action instance.
    """
    for action in action_list:
        if len(action.dependency_keys) > 0:
            try:
                any(
                    action.add_dependency(actions.Dependency(obj))
                    for obj in [object_mapping[key] for key in action.dependency_keys]
                )
            except KeyError as err:
                utils.log_and_raise(
                    logger.error,
                    KeyError,
                    f"Dependency key {err.args[0]} does not refer to an object that exists.",
                    errors.GP_BAD_DEPENDENCY_REF,
                )


def _build_nodes(
    action_list: List[Action], object_node_mapping: Dict[Action, GraphNode[Action]]
) -> None:
    """Builds GraphNodes based on actions with dependencies.

    Args:
        action_list: The list of all actions.
        object_node_mapping: A mapping from action instance to the GraphNode instance that contains it.
    """
    for action in action_list:
        if len(action.dependencies) > 0:
            try:
                node = object_node_mapping[action]
                any(
                    node.add_child(dep_node)
                    for dep_node in [
                        object_node_mapping[dep_obj]
                        for dep_obj in [dep.value for dep in action.dependencies]
                    ]
                )
            except KeyError as err:
                utils.log_and_raise(
                    logger.error,
                    KeyError,
                    f"Coudldn't find execution graph node for object with key {err.args[0]}",
                )


def _build_root(
    action_list: List[Action],
    key_object_mapping: Dict[str, object],
    object_node_mapping: Dict[Action, GraphNode[Action]],
) -> GraphNode[Action]:
    """Attaches a root that depends on all actions with no existing dependencies.

    This is for convenience. See execution_graph.ExecutionGraph for details.

    Args:
        action_list: The list of all actions.
        key_object_mapping: The mapping from action.key to Action instance.
        object_node_mapping: The mapping from Action instance to GraphNode instance.

    Returns:
        A GraphNode containing the root action.
    """
    non_dependency_actions: Set[Action] = set()
    for action in action_list:
        for dep in action.dependencies:
            key = dep.value.key
            non_dependency_actions.add(key_object_mapping[key])

    top_nodes = set(action_list) - non_dependency_actions
    unused_key = str(uuid.uuid1())
    root_node: GraphNode[Action] = GraphNode(actions.NullAction(key=unused_key))

    any(root_node.add_child(object_node_mapping[node]) for node in top_nodes)
    return root_node


def _build_execution_graph(parser_state: ParserState) -> ExecutionGraph:
    """Builds the execution tree after actions and dependencies are isntantiated."""
    _build_nodes(parser_state.action_list, parser_state.object_node_mapping)
    root = _build_root(
        parser_state.action_list,
        parser_state.key_object_mapping,
        parser_state.object_node_mapping,
    )
    return ExecutionGraph(root, parser_state.condition_list)


def parse_execution_graph(path: Union[pathlib.Path, os.PathLike]) -> ExecutionGraph:
    """Creates an ExecutionGraph from configuration input.

    Does so by:
        1. Parsing config from YAML file
        2. Building actions
        3. Building dependencies between actions
        4. Using action dependencies to construct a directed graph

    Args:
         path: The path of the input file.

    Returns:
        The complete ExecutionGraph.
    """
    config = _get_config(path)

    parser_state = _parse_objects(config)

    _build_dependency_graph(parser_state.action_list, parser_state.key_object_mapping)

    return _build_execution_graph(parser_state)
