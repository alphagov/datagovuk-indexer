import asyncio
from datetime import UTC, date, datetime
from logging import getLogger
from typing import TYPE_CHECKING
from uuid import uuid5

import boto3
from opensearchpy import AsyncOpenSearch, AWSV4SignerAuth, OpenSearch, RequestsHttpConnection, helpers
from psycopg.rows import dict_row

if TYPE_CHECKING:
    from psycopg import AsyncConnection

from config import config
from indexer import database, utils
from indexer.datagovuk import get_datagovuk_collections

logger = getLogger(__file__)


class BadlyConfiguredError(Exception):
    pass


def get_client():
    if not config.OPENSEARCH_URL:
        message = "Missing OPENSEARCH_URL config variable"
        raise BadlyConfiguredError(message)

    session = boto3.Session()
    credentials = session.get_credentials()
    region = config.AWS_REGION
    awsauth = AWSV4SignerAuth(credentials, region)
    return OpenSearch(hosts=[config.OPENSEARCH_URL], http_auth=awsauth, connection_class=RequestsHttpConnection)


def setup_index():
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
                    "slug": {"type": "keyword"},
                    "collection": {"type": "keyword"},
                    "source": {"type": "keyword"},
                    "title": {
                        "type": "text",
                        "fields": {
                            "keyword": {"type": "keyword", "ignore_above": 256},
                            "english": {"type": "text", "analyzer": "english"},
                        },
                    },
                    "description": {
                        "type": "text",
                        "fields": {
                            "keyword": {"type": "keyword", "ignore_above": 256},
                            "english": {"type": "text", "analyzer": "english"},
                        },
                    },
                    "description_raw": {
                        "type": "text",
                        "fields": {
                            "keyword": {"type": "keyword", "ignore_above": 256},
                        },
                    },
                    "organisations": {
                        "type": "object",
                        "properties": {
                            "uuid": {"type": "keyword"},
                            "slug": {
                                "type": "keyword",
                                "normalizer": "lowercase_normalizer",
                            },
                            "name": {
                                "type": "text",
                                "fields": {
                                    "keyword": {"type": "keyword", "ignore_above": 256},
                                    "english": {"type": "text", "analyzer": "english"},
                                },
                            },
                        },
                    },
                    "created_at": {"type": "date"},
                    "updated_at": {"type": "date"},
                },
            },
        },
        "priority": config.DATASETS_INDEX["priority"],
    }

    client = get_client()
    template_name = f"{datasets_prefix}template"
    client.indices.put_index_template(name=template_name, body=datasets_template)
    logger.info("Index template '%s' configured.", template_name)


def transform_context(context):
    """
    Recursively transform keys frontmatter kebab-case to pythonic underscores, e.g.
    my-key becomes my_key
    """
    if isinstance(context, dict):
        return {key.lower().replace("-", "_"): transform_context(value) for key, value in context.items()}
    if isinstance(context, list):
        return [transform_context(item) for item in context]
    return context


async def fetch_ckan_documents(
    conn: AsyncConnection,
    index_name,
    row_limit=None,
    created_since=None,
):
    query = """
        SELECT
            p.id,
            p.title,
            p.name,
            p.notes,
            p.metadata_created,
            p.metadata_modified,
            org.name AS org_slug,
            org.id AS org_id,
            org.title AS org_name
        FROM package AS p
        INNER JOIN "group" AS org ON p.owner_org=org.id
        WHERE p.state='active'
    """
    if created_since:
        query += """
        AND p.metadata_created >= %(created_since)s
        """
    query += """
        ORDER BY p.metadata_created, p.id
    """
    if row_limit:
        query += f"""
        LIMIT {row_limit}
        """
    async with conn.cursor(name="package_stream_cursor") as cursor:
        cursor.itersize = config.POSTGRES_BATCH_SIZE
        await cursor.execute(query, {"created_since": created_since})

        async for row in cursor:
            stripped_description = await utils.strip_markdown_and_html(row["notes"])
            yield {
                "_index": index_name,
                "_id": str(row["id"]),
                "_source": {
                    "uuid": row["id"],
                    "title": row["title"],
                    "slug": row["name"],
                    "source": "ckan",
                    "description_raw": row["notes"],
                    "description": stripped_description,
                    "created_at": row["metadata_created"],
                    "updated_at": row["metadata_modified"],
                    "organisations": [
                        {
                            "uuid": row["org_id"],
                            "name": row["org_name"],
                            "slug": row["org_slug"],
                        },
                    ],
                },
            }


async def _opensearch_index_ckan(index_name, row_limit=None, created_since=None):
    async with await database.connect(row_factory=dict_row) as pg_conn:
        opensearch_client = AsyncOpenSearch(hosts=[config.OPENSEARCH_URL])

        logger.info("Starting streaming pipeline from Postgres (psycopg3) to OpenSearch...")

        success_count = 0
        failure_count = 0
        errors = []
        async for success, info in helpers.async_streaming_bulk(
            client=opensearch_client,
            actions=fetch_ckan_documents(pg_conn, index_name, row_limit=row_limit, created_since=created_since),
            chunk_size=config.POSTGRES_BATCH_SIZE,
            max_chunk_bytes=10 * 1024 * 1024,  # 10 MB chunk limit
            raise_on_error=False,
        ):
            if success:
                success_count += 1
            else:  # pragma: no cover
                # TODO: Remove pragma:no cover above when the mapping gets more complex;
                #   it's currently too tricky to trigger this without lots of mocking
                failure_count += 1
                errors.append(info)
                logger.warning("Failed to index document: %s", info)

        logger.info("Indexing complete! Successfully indexed %s documents.", success_count)

        await opensearch_client.close()
        return {
            "success_count": success_count,
            "failure_count": failure_count,
            "errors": errors,
        }


def get_collections(index_name):
    collections = get_datagovuk_collections()
    # TODO: created_at requires a date and for now we are using a fixed date as a placeholder
    for collection in collections:
        collection_name = collection["name"]
        for topic in collection.get("topics", []):
            topic_uuid = uuid5(config.NAMESPACE_UUID, collection_name + topic["slug"])
            stripped_description = utils.strip_markdown_html(topic["description"])
            yield {
                "_index": index_name,
                "_id": str(topic_uuid),
                "_source": transform_context(
                    {
                        "title": topic["title"],
                        "source": "collection",
                        "collection": collection_name,
                        "uuid": topic_uuid,
                        "slug": topic["slug"],
                        "description": stripped_description,
                        "description_raw": topic["description"],
                        "organisations": [],
                        "created_at": "2024-06-06T00:00:00Z",
                        "updated_at": topic["page-last-updated"],
                    },
                ),
            }


def index_collections(index_name):
    logger.info("Indexing collections")
    opensearch_client = get_client()
    success_count, errors = helpers.bulk(
        opensearch_client,
        get_collections(index_name=index_name),
        raise_on_error=False,
    )
    logger.info("Indexed %s collection documents.", success_count)
    if errors:
        logger.warning("Failed to index %s collection documents due to errors: %s", len(errors), errors)
    return success_count


def index_ckan(index_name, row_limit=None, created_since: date | None = None):
    logger.info("Indexing ckan datasets")
    results = asyncio.run(
        _opensearch_index_ckan(index_name=index_name, row_limit=row_limit, created_since=created_since),
    )
    logger.info("Successfully Indexed %s ckan documents.", results["success_count"])
    if results["failure_count"]:
        logger.warning(
            "Failed to index %s ckan documents due to errors: %s",
            results["failure_count"],
            results["errors"],
        )
    return results["success_count"]


def index_opensearch(ckan_row_limit=None, ckan_created_since: date | None = None):
    index_suffix = datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace(":", ".").replace("T", "t")
    index_name = f"{config.DATASETS_INDEX['name']}-{index_suffix}"

    setup_index()
    collections_success_count = index_collections(index_name=index_name)

    if collections_success_count == 0:
        logger.error("Failed to index collections.")
        delete_index(index_name)
        return False

    if config.FEATURE_FLAG_INDEX_CKAN:
        ckan_success_count = index_ckan(
            index_name=index_name,
            row_limit=ckan_row_limit,
            created_since=ckan_created_since,
        )
        if ckan_success_count == 0:
            logger.error("Failed to index CKAN datasets/packages.")
            delete_index(index_name)
            return False

    publish_index(index_name)
    return True


def delete_index(index_name):
    logger.info("Deleting index %s...", index_name)
    get_client().indices.delete(index=index_name, ignore=[404])
    logger.info("Index %s deleted.", index_name)


def publish_index(index_name):
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
    logger.info("Clearing indeces...")
    opensearch_client = get_client()
    datasets_prefix = f"{config.DATASETS_INDEX['name']}-"
    opensearch_client.indices.delete(index=f"{datasets_prefix}*")
    logger.info("Clearing index templates...")
    template_name = f"{datasets_prefix}template"
    opensearch_client.indices.delete_index_template(name=template_name)
    logger.info("Clearing opensearch complete.")
