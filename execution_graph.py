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
    """Represents a single node in a directed graph.

    One unique feature is the way that visits are tracked. Visits are tracked in the
    context of a unique value, so that subsequent visits can be tracked without
    traversing the graph and resetting.

    Attributes:
        parents: The GraphNodes that point to this GraphNode.
        children: The GraphNodes that this GraphNode points to.
        value: The value contained by this node.
    """

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
        """Determines if the graph was visited with the visit key 'key'.

        Args:
            key: See class docstring.

        Returns:
            True if the node was visited with the given key.
        """
        return self._visited.get(key, False)

    def set_visited(self, key: str) -> None:
        """Sets the node as visited in the context of `key`.

        Args:
            key: See class docstring.
        """
        self._visited[key] = True


class CircularDependencyException(BaseException):
    pass


class ExecutionGraph(object):
    """A graph that allows actions to be executed in an order that is appropriate given
       dependencies.

    Attributes:
         execution_root: An artificial "root" that contains pointers to all real actions
            without incoming edges, in order to create a topological ordering.
        environment_conditions: The global conditions necessary for the execution graph
            to run. Not yet implemented.
    """

    def __init__(
        self,
        execution_root: GraphNode[Action],
        environment_conditions: List[actions.EnvironmentCondition],
    ):
        self._root: GraphNode[Action] = execution_root
        self._environment_conditions = environment_conditions

    def execute(self):
        """Executes all actions after getting a topological sort.

        Not tolerant to any individual node failure. Actions should be written in an idempotent way, as the execution
        graph has no way to roll back on failure.
        """
        topological_sort = self.get_topological_sort()
        execute_order = reversed(topological_sort)

        # TODO: Consider allowing partial executions again
        for node in execute_order:
            try:
                node.value.execute()
            except actions.ActionFailureException as err:
                raise err

    def get_topological_sort(self) -> List[GraphNode[Action]]:
        """Get's the topological sort to account for dependencies.

        Uses a modified version of Kahn's algorithm.
        """
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

    def check_conditions(self):
        """Runs EnvironmentConditions to ensure that all are met for the execution graph
        to run."""
        raise NotImplementedError()
