import argparse
import logging
import sys
from datetime import UTC, datetime

from indexer.opensearch import clear_opensearch, configure_mappings, index_ckan_and_collections

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
        "--row-limit",
        type=int,
        default=None,
        help="Maximum rows to index",
    )

    subparsers.add_parser("clear", help="Clear opensearch")

    args = parser.parse_args()

    if args.operation == "index":
        configure_mappings()
        suffix = datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace(":", ".").replace("T", "t")
        index_ckan_and_collections(row_limit=args.row_limit, suffix=suffix)
    elif args.operation == "clear":
        clear_opensearch()


if __name__ == "__main__":
    main()
