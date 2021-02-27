import argparse
import tree_parser

parser = argparse.ArgumentParser()

parser.add_argument("--path", type=str)


def main():
    args = parser.parse_args()
    execution_tree = tree_parser.parse_execution_tree(args.path)
    execution_tree.execute()


if __name__ == "__main__":
    main()
