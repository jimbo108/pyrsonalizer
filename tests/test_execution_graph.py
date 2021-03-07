import uuid

import pytest

import execution_graph
from actions import Action
from execution_context import ExecutionContext

VISITED_COUNT = 0


class TestAction(Action):
    def execute(self, exec_context: ExecutionContext):
        global VISITED_COUNT
        VISITED_COUNT += 1


class TestExecutionGraph:
    def test_circular_dependency__raises(self):
        node_one = execution_graph.GraphNode(TestAction("1"))
        node_two = execution_graph.GraphNode(TestAction("2"))
        node_three = execution_graph.GraphNode(TestAction("3"))
        node_four = execution_graph.GraphNode(TestAction("4"))

        node_one.add_child(node_two)
        node_two.add_child(node_three)
        node_three.add_child(node_four)
        node_four.add_child(node_two)

        exec_graph = execution_graph.ExecutionGraph(node_one, [])
        with pytest.raises(execution_graph.CircularDependencyException):
            exec_graph.execute(ExecutionContext())

    def test_happy_path__all_nodes_executed(self):
        node_one = execution_graph.GraphNode(TestAction("1"))
        node_two = execution_graph.GraphNode(TestAction("2"))
        node_three = execution_graph.GraphNode(TestAction("3"))
        node_four = execution_graph.GraphNode(TestAction("4"))

        node_one.add_child(node_two)
        node_one.add_child(node_four)
        node_two.add_child(node_three)
        node_three.add_child(node_four)

        exec_graph = execution_graph.ExecutionGraph(node_one, [])
        try:
            exec_graph.execute(ExecutionContext())
        except:
            pytest.fail()

        global VISITED_COUNT
        assert VISITED_COUNT == 4
        VISITED_COUNT = 0
