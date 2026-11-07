"""Knowledge Graph Command-Line Interface."""
import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="Knowledge Graph & Search CLI")
    sub = parser.add_subparsers(dest="command")

    search_p = sub.add_parser("search", help="Search knowledge base")
    search_p.add_argument("query", help="Query string")

    stats_p = sub.add_parser("stats", help="Show graph statistics")

    args = parser.parse_args()
    if args.command == "stats":
        print("Nodes: 0 | Edges: 0")
    elif args.command == "search":
        print(f"Searching for: {args.query}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
