from typing import List, TypeVar, Generic, Optional, Dict
import uuid

from actions import Action
import actions

T = TypeVar("T")


class TreeNode(Generic[T]):
    def __init__(self, value: T = None):
        self._child_nodes: List[TreeNode[T]] = []
        self._visited: Dict[str, bool] = {}
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
    def parents(self) -> List["TreeNode[T]"]:
        return self._parent_nodes

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
    def __init__(self, execution_root: TreeNode[Action], environment_conditions: List[actions.EnvironmentCondition]):
        self._root: TreeNode[Action] = execution_root
        self._environment_conditions = environment_conditions

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
            self._get_leaves_inner(child, key, leaves)

        node.set_visited(key)

    def execute(self):
        leaves = self._get_leaves()
        for leaf_node in leaves:
            self._execute_inner(leaf_node)

    def _execute_inner(self, node: TreeNode[Action]) -> None:
        success = node.value.execute()
        if not success:
            return
        for parent_node in node.parents:
            self._execute_inner(parent_node)

    def check_conditions(self):
        raise NotImplementedError()
