from typing import Any, Type, Union, Set, List, Dict, Callable
import yaml
import pathlib
import os
import logging
from dataclasses import dataclass, field

import utils
import actions
from execution_tree import ExecutionTree, TreeNode
from actions import Action
import node_parsers

import const

logger = logging.Logger(__file__)

KLASS_MAP = {
    "file_syncs": actions.FileSync,
    "installation": actions.Installation,
    "environment_condition": actions.EnvironmentCondition,
}

PARSER_MAP: Dict[Type, Callable] = {actions.FileSync: node_parsers.parse_file_sync}


@dataclass
class ParserState:
    action_list: List[Action] = field(default_factory=lambda: [])
    key_object_mapping: Dict[int, object] = field(default_factory=lambda: {})
    object_node_mapping: Dict[Action, TreeNode[Action]] = field(
        default_factory=lambda: {}
    )
    condition_list: List[actions.EnvironmentCondition] = field(
        default_factory=lambda: []
    )


def _handle_add_action(action: Action, parser_state: ParserState) -> None:
    parser_state.action_list.append(action)
    parser_state.key_object_mapping[action.key] = action
    node = TreeNode(value=action)
    parser_state.object_node_mapping[action] = node


def _get_klass_for_node(node: str) -> Type:
    klass = KLASS_MAP.get(node, None)
    if klass is None:
        utils.log_and_raise(
            logger.error, ValueError, f"Couldn't map yaml node {node} to a class."
        )
    return klass


def _get_config(path: Union[pathlib.Path, os.PathLike]) -> Dict[str, Any]:
    if not os.path.exists(path):
        utils.log_and_raise(
            logger.error, ValueError, f"Path {str(path)} does not exist."
        )

    with open(path) as fh:
        return yaml.load(fh, Loader=yaml.BaseLoader)


def _parse_objects(
    config: Dict[str, Any],
) -> ParserState:
    parser_state = ParserState()
    for key in config.keys():
        klass = _get_klass_for_node(key)
        parser_func = PARSER_MAP[klass]
        for obj_config in config[key]:
            instance = parser_func(obj_config)
            if issubclass(klass, Action):
                _handle_add_action(instance, parser_state)

            elif issubclass(klass, actions.EnvironmentCondition):
                parser_state.condition_list.append(instance)

    return parser_state


def _build_dependency_tree(
    action_list: List[Action], object_mapping: Dict[int, object]
) -> None:
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
                )


def _build_nodes(
    action_list: List[Action], object_node_mapping: Dict[Action, TreeNode[Action]]
) -> None:
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
                    f"Coudldn't find execution tree node for object with key {err.args[0]}",
                )


def _build_root(
    action_list: List[Action],
    key_object_mapping: Dict[int, object],
    object_node_mapping: Dict[Action, TreeNode[Action]],
) -> TreeNode[Action]:
    actions_with_dependencies: Set[Action] = set()
    for action in action_list:
        if len(action.dependencies) > 0:
            actions_with_dependencies.add(action)

    top_nodes = set(action_list) - actions_with_dependencies
    unused_key = max([int(key) for key in key_object_mapping.keys()]) + 1
    root_node: TreeNode[Action] = TreeNode(actions.NullAction(key=unused_key))

    any(root_node.add_child(object_node_mapping[node]) for node in top_nodes)
    return root_node


def _build_execution_tree(parser_state: ParserState) -> ExecutionTree:
    _build_nodes(parser_state.action_list, parser_state.object_node_mapping)
    root = _build_root(
        parser_state.action_list,
        parser_state.key_object_mapping,
        parser_state.object_node_mapping,
    )
    return ExecutionTree(root, parser_state.condition_list)


def parse_execution_tree(path: Union[pathlib.Path, os.PathLike]):
    config = _get_config(path)

    parser_state = _parse_objects(config)

    _build_dependency_tree(parser_state.action_list, parser_state.key_object_mapping)
    breakpoint()
    return _build_execution_tree(parser_state)
