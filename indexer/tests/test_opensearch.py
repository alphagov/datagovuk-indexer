from datetime import UTC, date, datetime
from unittest.mock import patch
from uuid import uuid5

import opensearchpy
import pytest
from freezegun import freeze_time

from config import config
from indexer import opensearch


def test_get_client_no_opensearch_url_raises_exception():
    old_opensearch_url = config.OPENSEARCH_URL
    config.OPENSEARCH_URL = None
    with pytest.raises(opensearch.BadlyConfiguredError):
        opensearch.get_client()
    config.OPENSEARCH_URL = old_opensearch_url


def test_get_client_success():
    client = opensearch.get_client()
    assert client.ping() is True


def _get_template_properties(client, template_name):
    templates = client.indices.get_index_template(name=template_name)
    assert templates["index_templates"][0]["name"] == template_name
    return templates["index_templates"][0]["index_template"]["template"]["mappings"]["properties"]


def test_setup_indices_adds_index_templates_successfully(
    opensearch_datasets_template_name,
    opensearch_collections_template_name,
    opensearch_client,
):
    opensearch.setup_indices()

    datasets_properties = _get_template_properties(opensearch_client, opensearch_datasets_template_name)
    assert datasets_properties["uuid"]["type"] == "keyword"
    assert "collection" not in datasets_properties

    collections_properties = _get_template_properties(opensearch_client, opensearch_collections_template_name)
    assert collections_properties["uuid"]["type"] == "keyword"
    assert collections_properties["collection"]["type"] == "keyword"


def _get_utc(dt):
    return dt.replace(tzinfo=None)


def test_index_opensearch_correctly(
    collection_factory,
    collections_with_topics,
    package_factory,
    configured_opensearch_client,
    opensearch_datasets_name,
    opensearch_collections_name,
):
    collection = collections_with_topics[0]
    topic = collection["topics"][0]
    topic_uuid = uuid5(config.NAMESPACE_UUID, collection["name"] + topic["slug"])

    package_1, org_1 = package_factory()
    package_2, org_2 = package_factory()

    opensearch_client = configured_opensearch_client

    opensearch.index_opensearch()

    indexed_package_1 = opensearch_client.get(
        index=f"{opensearch_datasets_name}",
        id=str(package_1["id"]),
    )["_source"]
    assert indexed_package_1["title"] == package_1["title"]
    assert indexed_package_1["slug"] == package_1["name"]
    assert indexed_package_1["description_raw"] == package_1["notes"]
    assert indexed_package_1["created_at"] == _get_utc(package_1["metadata_created"]).isoformat()
    assert indexed_package_1["updated_at"] == _get_utc(package_1["metadata_modified"]).isoformat()
    assert indexed_package_1["organisations"][0]["uuid"] == package_1["owner_org"]
    assert indexed_package_1["organisations"][0]["slug"] == org_1["name"]
    assert indexed_package_1["organisations"][0]["name"] == org_1["title"]

    indexed_package_2 = opensearch_client.get(
        index=f"{opensearch_datasets_name}",
        id=str(package_2["id"]),
    )["_source"]
    assert indexed_package_2["title"] == package_2["title"]
    assert indexed_package_2["slug"] == package_2["name"]
    assert indexed_package_2["description_raw"] == package_2["notes"]
    assert indexed_package_2["created_at"] == _get_utc(package_2["metadata_created"]).isoformat()
    assert indexed_package_2["updated_at"] == _get_utc(package_2["metadata_modified"]).isoformat()
    assert indexed_package_2["organisations"][0]["uuid"] == package_2["owner_org"]
    assert indexed_package_2["organisations"][0]["slug"] == org_2["name"]
    assert indexed_package_2["organisations"][0]["name"] == org_2["title"]

    indexed_collection = opensearch_client.get(
        index=f"{opensearch_collections_name}",
        id=str(topic_uuid),
    )["_source"]
    assert indexed_collection["title"] == topic["title"]
    assert indexed_collection["slug"] == "test-topic"
    assert indexed_collection["collection"] == "collection-name"
    assert indexed_collection["description"] == "Test description"
    assert indexed_collection["description_raw"] == topic["description"]
    assert indexed_collection["organisations"] == []
    assert indexed_collection["updated_at"] == topic["page-last-updated"]

    with pytest.raises(opensearchpy.exceptions.NotFoundError):
        opensearch_client.get(index=opensearch_datasets_name, id=str(topic_uuid))
    with pytest.raises(opensearchpy.exceptions.NotFoundError):
        opensearch_client.get(index=opensearch_collections_name, id=str(package_1["id"]))


def test_index_opensearch_with_deleted_package_not_indexed(
    collection_factory,
    package_factory,
    configured_opensearch_client,
    opensearch_datasets_name,
):
    active_package, active_org = package_factory()
    deleted_package, _ = package_factory(state="deleted")
    opensearch_client = configured_opensearch_client

    opensearch.index_opensearch()

    indexed_active_package = opensearch_client.get(
        index=f"{opensearch_datasets_name}",
        id=str(active_package["id"]),
    )["_source"]
    assert indexed_active_package["title"] == active_package["title"]
    assert indexed_active_package["slug"] == active_package["name"]
    assert indexed_active_package["description_raw"] == active_package["notes"]
    assert indexed_active_package["created_at"] == _get_utc(active_package["metadata_created"]).isoformat()
    assert indexed_active_package["updated_at"] == _get_utc(active_package["metadata_modified"]).isoformat()
    assert indexed_active_package["organisations"][0]["uuid"] == active_package["owner_org"]
    assert indexed_active_package["organisations"][0]["slug"] == active_org["name"]
    assert indexed_active_package["organisations"][0]["name"] == active_org["title"]

    with pytest.raises(opensearchpy.exceptions.NotFoundError):
        opensearch_client.get(index=f"{opensearch_datasets_name}", id=str(deleted_package["id"]))


def test_index_opensearch_with_no_indexing(
    no_collections,
    configured_opensearch_client,
    opensearch_datasets_name,
):
    opensearch_client = configured_opensearch_client
    result = opensearch.index_opensearch()

    assert result is False
    with pytest.raises(opensearchpy.exceptions.NotFoundError):
        opensearch_client.get(index=f"{opensearch_datasets_name}", id="nonexistent")


def test_index_opensearch_fails_if_no_collections(
    no_collections,
    package_factory,
    configured_opensearch_client,
    opensearch_datasets_prefix,
    opensearch_collections_prefix,
):
    package_factory()
    result = opensearch.index_opensearch()
    assert result is False
    assert not configured_opensearch_client.indices.get(index=f"{opensearch_datasets_prefix}*", ignore=[404])
    assert not configured_opensearch_client.indices.get(index=f"{opensearch_collections_prefix}*", ignore=[404])


@freeze_time("2026-08-28")
def test_index_opensearch_fails_if_no_ckan(
    collection_factory,
    configured_opensearch_client,
    opensearch_datasets_prefix,
    opensearch_collections_name,
):
    result = opensearch.index_opensearch()
    assert result is False
    assert not configured_opensearch_client.indices.get(index=f"{opensearch_datasets_prefix}*", ignore=[404])
    # Collections are indexed and published before CKAN, so they remain available
    collections_aliases = configured_opensearch_client.indices.get_alias(name=opensearch_collections_name)
    assert list(collections_aliases.keys()) == [f"{opensearch_collections_name}-2026-08-28t00.00.00+00.00"]


def test_index_opensearch_alias_moves_on_reindex(
    collection_factory,
    package_factory,
    configured_opensearch_client,
    opensearch_datasets_name,
    opensearch_collections_name,
):
    package_factory()
    opensearch_client = configured_opensearch_client

    with freeze_time("2026-08-28"):
        opensearch.index_opensearch()
    first_datasets_aliases = opensearch_client.indices.get_alias(name=opensearch_datasets_name)
    first_collections_aliases = opensearch_client.indices.get_alias(name=opensearch_collections_name)

    package_factory()
    with freeze_time("2026-08-29"):
        opensearch.index_opensearch()
    second_datasets_aliases = opensearch_client.indices.get_alias(name=opensearch_datasets_name)
    second_collections_aliases = opensearch_client.indices.get_alias(name=opensearch_collections_name)

    first_datasets_index = f"{opensearch_datasets_name}-2026-08-28t00.00.00+00.00"
    first_collections_index = f"{opensearch_collections_name}-2026-08-28t00.00.00+00.00"
    assert list(first_datasets_aliases.keys()) == [first_datasets_index]
    assert list(first_collections_aliases.keys()) == [first_collections_index]
    assert list(second_datasets_aliases.keys()) == [f"{opensearch_datasets_name}-2026-08-29t00.00.00+00.00"]
    assert list(second_collections_aliases.keys()) == [f"{opensearch_collections_name}-2026-08-29t00.00.00+00.00"]

    aliases = opensearch_client.indices.get_alias(index=first_datasets_index)
    assert opensearch_datasets_name not in aliases[first_datasets_index]["aliases"]
    aliases = opensearch_client.indices.get_alias(index=first_collections_index)
    assert opensearch_collections_name not in aliases[first_collections_index]["aliases"]


def test_publish_index_only_moves_given_alias(
    configured_opensearch_client,
    opensearch_datasets_name,
    opensearch_collections_name,
):
    opensearch_client = configured_opensearch_client
    datasets_index = f"{opensearch_datasets_name}-x"
    collections_index = f"{opensearch_collections_name}-x"
    opensearch_client.indices.create(index=datasets_index)
    opensearch_client.indices.create(index=collections_index)

    opensearch.publish_index(index_name=datasets_index, index_alias=opensearch_datasets_name)
    opensearch.publish_index(index_name=collections_index, index_alias=opensearch_collections_name)

    datasets_aliases = opensearch_client.indices.get_alias(name=opensearch_datasets_name)
    collections_aliases = opensearch_client.indices.get_alias(name=opensearch_collections_name)
    assert list(datasets_aliases.keys()) == [datasets_index]
    assert list(collections_aliases.keys()) == [collections_index]


def test_index_opensearch_with_ckan_row_limit(
    collection_factory,
    package_factory,
    configured_opensearch_client,
    opensearch_datasets_name,
):
    package_1, _ = package_factory()
    package_2, _ = package_factory()
    opensearch_client = configured_opensearch_client

    opensearch.index_opensearch(ckan_row_limit=1)

    opensearch_client.get(index=opensearch_datasets_name, id=str(package_1["id"]))
    with pytest.raises(opensearchpy.exceptions.NotFoundError):
        opensearch_client.get(index=opensearch_datasets_name, id=str(package_2["id"]))


def test_index_opensearch_with_ckan_created_since(
    collection_factory,
    package_factory,
    configured_opensearch_client,
    opensearch_datasets_name,
):
    old_package, _ = package_factory(metadata_created=datetime(2023, 12, 31, 23, 59, 59, tzinfo=UTC))
    new_package, _ = package_factory(metadata_created=datetime(2024, 1, 1, tzinfo=UTC))
    opensearch_client = configured_opensearch_client

    opensearch.index_opensearch(ckan_created_since=date(2024, 1, 1))

    opensearch_client.get(index=opensearch_datasets_name, id=str(new_package["id"]))
    with pytest.raises(opensearchpy.exceptions.NotFoundError):
        opensearch_client.get(index=opensearch_datasets_name, id=str(old_package["id"]))


def test_index_opensearch_with_ckan_row_limit_keeps_oldest_packages(
    collection_factory,
    package_factory,
    configured_opensearch_client,
    opensearch_datasets_name,
):
    newest_package, _ = package_factory(metadata_created=datetime(2024, 3, 1, tzinfo=UTC))
    oldest_package, _ = package_factory(metadata_created=datetime(2024, 1, 1, tzinfo=UTC))
    middle_package, _ = package_factory(metadata_created=datetime(2024, 2, 1, tzinfo=UTC))
    opensearch_client = configured_opensearch_client

    opensearch.index_opensearch(ckan_row_limit=2, ckan_created_since=date(2024, 1, 1))

    opensearch_client.indices.refresh(index=opensearch_datasets_name)
    results = opensearch_client.search(
        index=opensearch_datasets_name,
        body={"query": {"match_all": {}}, "sort": [{"created_at": "asc"}]},
    )
    indexed_ids = [hit["_id"] for hit in results["hits"]["hits"]]
    assert indexed_ids == [str(oldest_package["id"]), str(middle_package["id"])]
    assert str(newest_package["id"]) not in indexed_ids


@freeze_time("2026-08-28")
def test_clear_opensearch_clears_successfully(
    collection_factory,
    package_factory,
    configured_opensearch_client,
    opensearch_datasets_name,
    opensearch_datasets_template_name,
    opensearch_collections_name,
    opensearch_collections_template_name,
):
    package_factory()
    opensearch_client = configured_opensearch_client
    opensearch.index_opensearch()

    expected_index_names = [
        opensearch_datasets_name + "-2026-08-28t00.00.00+00.00",
        opensearch_collections_name + "-2026-08-28t00.00.00+00.00",
    ]
    expected_template_names = [opensearch_datasets_template_name, opensearch_collections_template_name]
    all_indices = list(opensearch_client.indices.get(index="*").keys())
    all_templates = [template["name"] for template in opensearch_client.indices.get_index_template()["index_templates"]]
    for index_name in expected_index_names:
        assert index_name in all_indices
    for template_name in expected_template_names:
        assert template_name in all_templates

    opensearch.clear_opensearch()

    all_indices = list(opensearch_client.indices.get(index="*").keys())
    all_templates = [template["name"] for template in opensearch_client.indices.get_index_template()["index_templates"]]
    for index_name in expected_index_names:
        assert index_name not in all_indices
    for template_name in expected_template_names:
        assert template_name not in all_templates


def test_transform_context_transforms_nested_list():
    result = opensearch.transform_context({"test-key": ["test1", "test2"]})
    assert result == {"test_key": ["test1", "test2"]}


def test_index_collections_logs_warning_on_errors(mock_bulk_with_error, caplog, collection_factory):
    opensearch.index_collections(index_name="collections-test-2026-01-01t00.00.00+00.00")
    assert "Failed to index 1 collection documents due to errors" in caplog.text


def test_index_ckan_logs_warning_on_failure(failing_bulk_index, caplog, package_factory):
    package_factory()
    result = opensearch.index_ckan(index_name="datasets-test-2026-01-01t00.00.00+00.00")
    assert result == 0
    assert "Failed to index document" in caplog.text


@patch("indexer.opensearch.get_datagovuk_collections", return_value=[])
def test_mapping_collections_from_json(mock_get_collections, collections_with_topics):
    mock_get_collections.return_value = collections_with_topics
    result = list(opensearch.get_collections(index_name="collections-test-2026-01-01t00.00.00+00.00"))
    assert result[0]["_source"]["title"] == "test topic"
    assert result[0]["_source"]["description"] == "Test description"
    assert result[0]["_source"]["description_raw"] == "Test <p>description</p>"
    assert result[0]["_source"]["created_at"] == "2024-06-06T00:00:00Z"
    assert result[0]["_source"]["updated_at"] == "2026-08-28T00:00:00Z"
    assert result[0]["_source"]["collection"] == "collection-name"
