from typing import List, TypeVar, Generic, Optional, Dict
import uuid
import logging

from actions import Action
import actions
import utils
import errors

T = TypeVar("T")

logger = logging.Logger(__file__)


class GraphNode(Generic[T]):
    def __init__(self, value: T = None):
        self._child_nodes: List[GraphNode[T]] = []
        self._visited: Dict[str, bool] = {}
        self._value: Optional[T] = value
        self._parent_nodes: List[GraphNode[T]] = []
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

    def add_child(self, child_node: "GraphNode[T]"):
        self._child_nodes.append(child_node)
        child_node.add_parent_node(self)

    def add_parent_node(self, parent_node: "GraphNode[T]") -> None:
        self._parent_nodes.append(parent_node)

    @property
    def parents(self) -> List["GraphNode[T]"]:
        return self._parent_nodes

    @property
    def value(self) -> Optional[T]:
        return self._value

    @value.setter
    def value(self, value) -> None:
        self._value = value

    @property
    def children(self) -> List["GraphNode[T]"]:
        return self._child_nodes

    def was_visited(self, key: str) -> bool:
        return self._visited.get(key, False)

    def set_visited(self, key: str) -> None:
        self._visited[key] = True


class CircularDependencyException(BaseException):
    pass

class ExecutionGraph(object):
    def __init__(
        self,
        execution_root: GraphNode[Action],
        environment_conditions: List[actions.EnvironmentCondition],
    ):
        self._root: GraphNode[Action] = execution_root
        self._environment_conditions = environment_conditions

    def execute(self):
        topological_sort = self.get_topological_sort()
        execute_order = reversed(topological_sort)

        # TODO: Consider allowing partial executions again
        for node in execute_order:
            try:
                node.value.execute()
            except actions.ActionFailureException as err:
                raise err

    def get_topological_sort(self):
        active_list = [self._root]
        sorted_list: List[GraphNode[Action]] = []
        known_node_count = self._get_num_nodes()
        key = str(uuid.uuid1())

        while len(active_list) > 0:
            node = active_list.pop()
            node.set_visited(key)
            sorted_list.append(node)

            for child in node.children:
                if any(not parent.was_visited(key) for parent in child.parents):
                    continue
                else:
                    active_list.append(child)

        if len(sorted_list) < known_node_count:
            utils.log_and_raise(
                logger.error,
                CircularDependencyException,
                "Found circular dependency in dependency graph.",
                errors.EG_CIRCULAR_DEPENDENCY,
            )
        elif len(sorted_list) > known_node_count:
            utils.log_and_raise(
                logger.error,
                errors.ImpossibleStateException,
                "Hit an impossible state, you've found a bug!",
                errors.EG_IMPOSSIBLE_STATE,
            )

        return sorted_list

    def _get_num_nodes(self) -> int:
        key = str(uuid.uuid1())
        search_list = [self._root]
        node_count = 0

        while len(search_list) > 0:
            node = search_list.pop()
            if node.was_visited(key):
                continue
            else:
                node.set_visited(key)
                search_list.extend(node.children)
                node_count += 1

        return node_count

    def _get_leaves(self) -> List[GraphNode[Action]]:
        leaves = []
        visited_key = str(uuid.uuid1())
        self._get_leaves_inner(self._root, visited_key, leaves)
        return leaves

    def _get_leaves_inner(
        self, node: GraphNode[Action], key: str, leaves: List[GraphNode[Action]]
    ):
        if node.was_visited(key):
            return

        if len(node.children) == 0:
            leaves.append(node)

        for child in node.children:
            self._get_leaves_inner(child, key, leaves)

        node.set_visited(key)

    def execute_old(self):
        leaves = self._get_leaves()
        for leaf_node in leaves:
            self._execute_inner(leaf_node)

    def _execute_inner(self, node: GraphNode[Action]) -> None:
        success = node.value.execute()
        if not success:
            return
        for parent_node in node.parents:
            self._execute_inner(parent_node)

    def check_conditions(self):
        raise NotImplementedError()
