import argparse
import graph_parser

parser = argparse.ArgumentParser()

parser.add_argument("--path", type=str)


def main():
    args = parser.parse_args()
    execution_graph = graph_parser.parse_execution_graph(args.path)
    execution_graph.execute()


if __name__ == "__main__":
    main()
