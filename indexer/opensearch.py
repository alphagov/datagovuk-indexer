import asyncio
from datetime import UTC, datetime
from logging import getLogger

import psycopg
from opensearchpy import AsyncOpenSearch, OpenSearch, helpers
from psycopg.rows import dict_row

from config import config

logger = getLogger(__file__)


class BadlyConfiguredError(Exception):
    pass


def get_client():
    if not config.OPENSEARCH_URL:
        message = "Missing OPENSEARCH_URL config variable"
        raise BadlyConfiguredError(message)
    return OpenSearch(hosts=[config.OPENSEARCH_URL])


def configure_mappings():
    datasets_prefix = f"{config.DATASETS_INDEX['name']}-"
    datasets_template = {
        "index_patterns": [f"{datasets_prefix}*"],
        "template": {
            "settings": {
                "number_of_shards": config.DATASETS_INDEX["settings"]["number_of_shards"],
                "number_of_replicas": config.DATASETS_INDEX["settings"]["number_of_replicas"],
                "analysis": {
                    "normalizer": {
                        "lowercase_normalizer": {
                            "type": "custom",
                            "filter": ["lowercase"],
                        },
                    },
                },
            },
            "mappings": {
                "properties": {
                    "uuid": {"type": "keyword"},
                    "title": {
                        "type": "text",
                        "fields": {
                            "keyword": {"type": "keyword", "ignore_above": 256},
                            "english": {"type": "text", "analyzer": "english"},
                        },
                    },
                },
            },
        },
        "priority": config.DATASETS_INDEX["priority"],
    }

    client = get_client()
    template_name = f"{datasets_prefix}template"
    client.indices.put_index_template(name=template_name, body=datasets_template)
    logger.info("Index template '%s' configured.", template_name)


async def fetch_ckan_documents(conn: psycopg.AsyncConnection, index_name, row_limit=None):
    query = """
        SELECT
            p.id,
            p.title
        FROM package p
        WHERE state='active'
    """
    if row_limit:
        query += f"""
        LIMIT {row_limit}
        """
    async with conn.cursor(name="package_stream_cursor") as cursor:
        cursor.itersize = config.POSTGRES_BATCH_SIZE
        await cursor.execute(query)

        async for row in cursor:
            yield {
                "_index": index_name,
                "_id": str(row["id"]),
                "_source": {
                    "uuid": row["id"],
                    "title": row["title"],
                },
            }


async def _index_ckan(index_name, row_limit=None):
    # Connect using psycopg3's AsyncConnection with dictionary row mapping
    async with await psycopg.AsyncConnection.connect(config.POSTGRES_DSN, row_factory=dict_row) as pg_conn:
        opensearch_client = AsyncOpenSearch(hosts=[config.OPENSEARCH_URL])

        logger.info("Starting streaming pipeline from Postgres (psycopg3) to OpenSearch...")

        success_count = 0
        failure_count = 0
        async for success, info in helpers.async_streaming_bulk(
            client=opensearch_client,
            actions=fetch_ckan_documents(pg_conn, index_name, row_limit=row_limit),
            chunk_size=config.POSTGRES_BATCH_SIZE,
            max_chunk_bytes=10 * 1024 * 1024,  # 10 MB chunk limit
            raise_on_error=False,
        ):
            if success:
                success_count += 1
            else:
                failure_count += 1
                logger.warning("Failed to index document: %s", info)

        logger.info("Indexing complete! Successfully indexed %s documents.", success_count)

        await opensearch_client.close()
        return {
            "success_count": success_count,
            "failure_count": failure_count,
        }


def index_ckan(row_limit=None):
    index_suffix = datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace(":", ".").replace("T", "t")
    index_name = f"{config.DATASETS_INDEX['name']}-{index_suffix}"
    index_results = asyncio.run(_index_ckan(index_name=index_name, row_limit=row_limit))
    if index_results["success_count"] == 0:
        logger.error("No documents were indexed! Exiting before pointing alias to new index...")
        return
    logger.info("Switching alias to new index...")
    opensearch_client = get_client()
    alias_body = {
        "actions": [
            {"remove": {"index": "*", "alias": config.DATASETS_INDEX["name"]}},
            {"add": {"index": index_name, "alias": config.DATASETS_INDEX["name"]}},
        ],
    }
    opensearch_client.indices.update_aliases(body=alias_body)
    logger.info("Alias updated.")


def clear_opensearch():
    opensearch_client = get_client()
    datasets_prefix = f"{config.DATASETS_INDEX['name']}-"
    opensearch_client.indices.delete(index=f"{datasets_prefix}*")
    template_name = f"{datasets_prefix}template"
    opensearch_client.indices.delete_index_template(name=template_name)
