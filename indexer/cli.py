import argparse
import logging
import sys

from indexer.opensearch import clear_opensearch, index_opensearch

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(levelname)s: %(asctime)s: %(message)s",
)


def main():
    parser = argparse.ArgumentParser(description="Index ckan datasets/datagovuk collections to opensearch.")
    subparsers = parser.add_subparsers(dest="operation", required=True)

    index_parser = subparsers.add_parser("index", help="Index both ckan and collections to opensearch")
    index_parser.add_argument(
        "--ckan-row-limit",
        type=int,
        default=None,
        help="Maximum rows to index",
    )

    subparsers.add_parser("clear", help="Clear opensearch")

    args = parser.parse_args()

    if args.operation == "index":
        index_opensearch(ckan_row_limit=args.ckan_row_limit)
    elif args.operation == "clear":
        clear_opensearch()


if __name__ == "__main__":
    main()
