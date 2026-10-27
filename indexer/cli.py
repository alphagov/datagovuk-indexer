import argparse
import logging
import sys
from datetime import date

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
    index_parser.add_argument(
        "--ckan-created-since",
        type=date.fromisoformat,
        default=None,
        help="Only index ckan datasets created on or after this date (YYYY-MM-DD)",
    )

    subparsers.add_parser("clear", help="Clear opensearch")

    args = parser.parse_args()

    if args.operation == "index":
        index_opensearch(ckan_row_limit=args.ckan_row_limit, ckan_created_since=args.ckan_created_since)
    elif args.operation == "clear":
        clear_opensearch()


if __name__ == "__main__":
    main()
