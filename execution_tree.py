from typing import List, TypeVar, Generic, Optional, Dict
import uuid
import os
import logging
import yaml
import pathlib
from abc import ABC
import abc

from .actions import Action
from . import utils

T = TypeVar("T")

logger = logging.Logger(__file__)


class TreeNode(Generic[T]):
    def __init__(self, value: T = None):
        self._child_nodes: List[TreeNode[T]] = []
        self._visited: Dict[str, bool] = False
        self._value: Optional[T] = value
        self._parent_nodes: List[TreeNode[T]] = []
        self._index: int = 0
        self._max: int = 0

    def __iter__(self):
        self._index = 0
        self._max = len(self._child_nodes)
        return self

    def __next__(self):
        if self._index >= self._max:
            raise StopIteration
        chosen_child = self._child_nodes[self._index]
        self._index += 1
        return chosen_child

    def add_child(self, child_node: "TreeNode[T]"):
        self._child_nodes.append(child_node)
        child_node.add_parent_node(self)

    def add_parent_node(self, parent_node: "TreeNode[T]") -> None:
        self._parent_nodes.append(parent_node)

    @property
    def value(self) -> Optional[T]:
        return self._value

    @value.setter
    def value(self, value) -> None:
        self._value = value

    @property
    def children(self) -> List["TreeNode[T]"]:
        return self._child_nodes

    def was_visited(self, key: str) -> bool:
        return self._visited.get(key, False)

    def set_visited(self, key: str) -> None:
        self._visited[key] = True


class ExecutionTree(object):
    def __init__(self, execution_root: TreeNode[Action]):
        self._root: TreeNode[Action] = execution_root

    def _get_leaves(self) -> List[TreeNode[Action]]:
        leaves = []
        visited_key = str(uuid.uuid1())
        self._get_leaves_inner(self._root, visited_key, leaves)
        return leaves

    def _get_leaves_inner(
        self, node: TreeNode[Action], key: str, leaves: List[TreeNode[Action]]
    ):
        if node.was_visited(key):
            return

        if len(node.children) == 0:
            leaves.append(node)

        for child in node.children:
            self._get_leaves_inner(child, key)

        node.set_visited(key)

    def execute(self):
        leaves = self._get_leaves()
        for leaf_node in leaves:
            leaf_node.value.execute()


class Parser(object):
    def __init__(self, path: pathlib.PurePath):
        if not os.path.exists(path):
            utils.log_and_raise(
                logger.error, ValueError, f"Path {str(path)} does not exist."
            )

        with open(path) as fh:
            self.dic = yaml.load(fh, Loader=yaml.BaseLoader)

    def parse(self) -> ExecutionTree:
        pass
