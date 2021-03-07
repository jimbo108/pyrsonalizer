import argparse
import logging

import graph_parser
import utils
import execution_context

logger = logging.Logger(__file__)

parser = argparse.ArgumentParser()

parser.add_argument("--path", type=str)


def main():
    args = parser.parse_args()
    config = utils.get_config(args.path, logger)

    exec_context = execution_context.create_execution_context(config)

    execution_graph = graph_parser.parse_execution_graph(args.path, exec_context)
    execution_graph.execute(exec_context)


if __name__ == "__main__":
    main()
