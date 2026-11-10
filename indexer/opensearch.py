import asyncio
import json
from datetime import UTC, date, datetime
from logging import getLogger
from typing import TYPE_CHECKING
from uuid import uuid5

import boto3
from opensearchpy import (
    AsyncHttpConnection,
    AsyncOpenSearch,
    AWSV4SignerAsyncAuth,
    AWSV4SignerAuth,
    OpenSearch,
    RequestsHttpConnection,
    helpers,
)
from psycopg.rows import dict_row

if TYPE_CHECKING:
    from psycopg import AsyncConnection

from config import config
from indexer import database, utils
from indexer.constants import ADDITIONAL_INFO_JSON_VALUE_KEYS, ADDITIONAL_INFO_RELEVANT_KEYS
from indexer.datagovuk import get_datagovuk_collections

logger = getLogger(__file__)


class BadlyConfiguredError(Exception):
    pass


def _get_aws_credentials():
    if not config.OPENSEARCH_URL:
        message = "Missing OPENSEARCH_URL config variable"
        raise BadlyConfiguredError(message)
    return boto3.Session().get_credentials()


def get_client() -> OpenSearch:
    credentials = _get_aws_credentials()
    awsauth = AWSV4SignerAuth(credentials, config.AWS_REGION)
    return OpenSearch(hosts=[config.OPENSEARCH_URL], http_auth=awsauth, connection_class=RequestsHttpConnection)


def get_async_client() -> AsyncOpenSearch:
    credentials = _get_aws_credentials()
    awsauth = AWSV4SignerAsyncAuth(credentials, config.AWS_REGION)
    return AsyncOpenSearch(hosts=[config.OPENSEARCH_URL], http_auth=awsauth, connection_class=AsyncHttpConnection)


def setup_indices():
    _setup_datasets_index()
    _setup_collections_index()


def _setup_datasets_index():
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
                    "resources": {
                        "type": "object",
                        "properties": {
                            "uuid": {"type": "keyword"},
                            "name": {
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
                            "format": {"type": "keyword", "normalizer": "lowercase_normalizer"},
                            "url": {
                                "type": "keyword",
                                "index": False,
                                "doc_values": False,
                            },
                            "resource_type": {"type": "keyword"},
                        },
                    },
                    "created_at": {"type": "date"},
                    "updated_at": {"type": "date"},
                    "additional_information": {
                        "type": "nested",
                        "properties": {
                            "key": {"type": "keyword"},
                            "value": {"type": "text"},
                        },
                    },
                    "is_harvested": {"type": "boolean"},
                },
            },
        },
        "priority": config.DATASETS_INDEX["priority"],
    }

    client = get_client()
    template_name = f"{datasets_prefix}template"
    client.indices.put_index_template(name=template_name, body=datasets_template)
    logger.info("Index template '%s' configured.", template_name)


def _setup_collections_index():
    collections_prefix = f"{config.COLLECTIONS_INDEX['name']}-"
    collections_template = {
        "index_patterns": [f"{collections_prefix}*"],
        "template": {
            "settings": {
                "number_of_shards": config.COLLECTIONS_INDEX["settings"]["number_of_shards"],
                "number_of_replicas": config.COLLECTIONS_INDEX["settings"]["number_of_replicas"],
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
        "priority": config.COLLECTIONS_INDEX["priority"],
    }

    client = get_client()
    template_name = f"{collections_prefix}template"
    client.indices.put_index_template(name=template_name, body=collections_template)
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


def extract_additional_information(package_extras):
    additional_information = []
    for item in package_extras:
        key = item.get("key")
        value = item.get("value")

        if key not in ADDITIONAL_INFO_RELEVANT_KEYS:
            continue

        if key in ADDITIONAL_INFO_JSON_VALUE_KEYS:
            try:
                valid_json = json.loads(value)
                value = json.dumps(valid_json)
            except json.JSONDecodeError, TypeError:
                logger.warning("Failed to parse JSON for key '%s' with value '%s'", key, value)
        elif key == "metadata-date":
            try:
                value = datetime.fromisoformat(value).isoformat() if value else None
            except ValueError:
                value = None
        additional_information.append({"key": key, "value": value})
    return additional_information


def parse_resource_type(extras):
    try:
        extras = json.loads(extras or "{}")
        return extras.get("resource-type", "data-link")
    except json.JSONDecodeError, TypeError:
        return "data-link"


async def fetch_ckan_documents(
    conn: AsyncConnection,
    index_name,
    row_limit=None,
    created_since=None,
):

    active_resources_subquery = """
        (
            SELECT res.package_id, jsonb_agg(
                jsonb_build_object(
                    'id', res.id,
                    'name', res.name,
                    'description', res.description,
                    'format', res.format,
                    'url', res.url,
                    'extras', res.extras,
                    'last_modified', res.last_modified,
                    'metadata_modified', res.metadata_modified,
                    'created', res.created,
                    'size', res.size
                ) ORDER BY res.created DESC, res.id
            ) AS resources
            FROM resource as res
            WHERE res.state = 'active'
            GROUP BY res.package_id
        )
    """

    query = f"""
        SELECT
            p.id,
            p.title,
            p.name,
            p.notes,
            p.metadata_created,
            p.metadata_modified,
            org.name AS org_slug,
            org.id AS org_id,
            org.title AS org_name,
            COALESCE(r.resources, '[]'::jsonb) AS resources,
            COALESCE(
                jsonb_agg(
                    jsonb_build_object('key', extra.key, 'value', extra.value)
                ) FILTER (WHERE extra.key IS NOT NULL),
                '[]'::jsonb
            ) AS package_extras
        FROM package AS p
        INNER JOIN "group" AS org ON p.owner_org=org.id
        LEFT JOIN ({active_resources_subquery}) AS r ON r.package_id = p.id
        LEFT JOIN package_extra AS extra ON extra.package_id = p.id
            AND extra.key IS NOT NULL
            AND extra.state = 'active'
        WHERE p.state='active'
    """  # noqa: S608
    # NOTE: when adjusting CKAN tables to read data from, also adjust `streamlined_tables` variable in justfile

    if created_since:
        query += """
        AND p.metadata_created >= %(created_since)s
        """

    query += """
        GROUP BY p.id, p.title, p.name, p.notes, p.metadata_created, p.metadata_modified,
            org.name, org.id, org.title, r.resources
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
            notes = row["notes"]
            if not notes:
                continue
            stripped_description = await utils.strip_markdown_and_html(notes)
            additional_information = extract_additional_information(row["package_extras"])
            is_harvested = bool(additional_information)
            yield {
                "_index": index_name,
                "_id": str(row["id"]),
                "_source": {
                    "uuid": row["id"],
                    "title": row["title"],
                    "slug": row["name"],
                    "description_raw": notes,
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
                    "resources": [
                        {
                            "uuid": resource["id"],
                            "name": resource["name"],
                            "description": resource["description"],
                            "format": resource["format"],
                            "url": resource["url"],
                            "resource_type": parse_resource_type(resource["extras"]),
                            "size": resource["size"],
                            "created": resource["created"],
                            "last_modified": resource["last_modified"],
                            "metadata_modified": resource["metadata_modified"],
                        }
                        for resource in row["resources"]
                    ],
                    "additional_information": additional_information,
                    "is_harvested": is_harvested,
                },
            }


async def _opensearch_index_ckan(index_name, row_limit=None, created_since=None):
    async with await database.connect(row_factory=dict_row) as pg_conn:
        opensearch_client = get_async_client()

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
            request_timeout=60,
            max_retries=config.OPENSEARCH_MAX_RETRIES,
            initial_backoff=config.OPENSEARCH_INITIAL_BACKOFF,
            max_backoff=config.OPENSEARCH_MAX_BACKOFF,
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

    setup_indices()

    collections_index_name = f"{config.COLLECTIONS_INDEX['name']}-{index_suffix}"
    collections_success_count = index_collections(index_name=collections_index_name)
    if collections_success_count == 0:
        logger.error("Failed to index collections.")
        delete_index(collections_index_name)
        return False
    publish_index(index_name=collections_index_name, index_alias=config.COLLECTIONS_INDEX["name"])

    if config.FEATURE_FLAG_INDEX_CKAN:
        datasets_index_name = f"{config.DATASETS_INDEX['name']}-{index_suffix}"
        ckan_success_count = index_ckan(
            index_name=datasets_index_name,
            row_limit=ckan_row_limit,
            created_since=ckan_created_since,
        )
        if ckan_success_count == 0:
            logger.error("Failed to index CKAN datasets/packages.")
            delete_index(datasets_index_name)
            return False
        publish_index(index_name=datasets_index_name, index_alias=config.DATASETS_INDEX["name"])

    return True


def delete_index(index_name):
    logger.info("Deleting index %s...", index_name)
    get_client().indices.delete(index=index_name, ignore=[404])
    logger.info("Index %s deleted.", index_name)


def publish_index(index_name, index_alias):
    logger.info("Switching alias '%s' to point to new index '%s'...", index_alias, index_name)
    opensearch_client = get_client()
    alias_body = {
        "actions": [
            {"remove": {"index": f"{index_alias}-*", "alias": index_alias}},
            {"add": {"index": index_name, "alias": index_alias}},
        ],
    }
    opensearch_client.indices.update_aliases(body=alias_body)
    logger.info("Alias updated.")


def clear_opensearch():
    logger.info("Clearing indeces...")
    opensearch_client = get_client()
    for index_config in (config.DATASETS_INDEX, config.COLLECTIONS_INDEX):
        prefix = f"{index_config['name']}-"
        opensearch_client.indices.delete(index=f"{prefix}*", ignore=[404])
        logger.info("Clearing index template for '%s'...", index_config["name"])
        opensearch_client.indices.delete_index_template(name=f"{prefix}template", ignore=[404])
    logger.info("Clearing opensearch complete.")
