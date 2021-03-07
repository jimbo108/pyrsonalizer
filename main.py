from typing import List
import argparse
import logging

import graph_parser
import utils
import execution_context

logger = logging.Logger(__file__)

parser = argparse.ArgumentParser()

parser.add_argument("--path", type=str)


def main(override_args: List[str] = None):
    args = None
    if override_args is not None:
        args = parser.parse_args(override_args)
    else:
        args = parser.parse_args()

    config = utils.get_config(args.path, logger)

    exec_context = execution_context.create_execution_context(config)

    execution_graph = graph_parser.parse_execution_graph(args.path, exec_context)
    execution_graph.execute(exec_context)


if __name__ == "__main__":
    main()
