import argparse
import logging
import sys

from indexer.opensearch import clear_opensearch, configure_mappings, index_ckan

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(levelname)s: %(asctime)s: %(message)s",
)


def main():
    parser = argparse.ArgumentParser(description="Index ckan datasets/datagovuk collections to opensearch.")
    subparsers = parser.add_subparsers(dest="operation", required=True)

    index_parser = subparsers.add_parser("index", help="Index data to opensearch")
    index_parser.add_argument(
        "--row-limit",
        type=int,
        default=None,
        help="Maximum rows to index",
    )

    subparsers.add_parser("clear", help="Clear opensearch")

    args = parser.parse_args()

    if args.operation == "index":
        configure_mappings()
        index_ckan(row_limit=args.row_limit)
    elif args.operation == "clear":
        clear_opensearch()


if __name__ == "__main__":
    main()
