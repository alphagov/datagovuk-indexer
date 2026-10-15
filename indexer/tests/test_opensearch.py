from unittest.mock import patch

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


def test_configure_mappings_adds_index_template_successfully(opensearch_datasets_template_name, opensearch_client):
    opensearch.configure_mappings()
    templates = opensearch_client.indices.get_index_template(name=opensearch_datasets_template_name)
    assert templates["index_templates"][0]["name"] == opensearch_datasets_template_name
    assert (
        templates["index_templates"][0]["index_template"]["template"]["mappings"]["properties"]["uuid"]["type"]
        == "keyword"
    )


def _get_utc(dt):
    return dt.replace(tzinfo=None)


def test_index_ckan_active_packages_indexed_correctly(
    package_factory,
    configured_opensearch_client,
    opensearch_datasets_name,
):
    active_package_1, active_org_1 = package_factory()

    active_package_2, active_org_2 = package_factory()

    deleted_package, _ = package_factory(state="deleted")
    opensearch_client = configured_opensearch_client
    suffix = "test"

    opensearch.index_ckan(index_name=f"{opensearch_datasets_name}-{suffix}")

    indexed_package_1 = opensearch_client.get(
        index=f"{opensearch_datasets_name}-{suffix}",
        id=str(active_package_1["id"]),
    )["_source"]
    assert indexed_package_1["title"] == active_package_1["title"]
    assert indexed_package_1["description_raw"] == active_package_1["notes"]
    assert indexed_package_1["created_at"] == _get_utc(active_package_1["metadata_created"]).isoformat()
    assert indexed_package_1["updated_at"] == _get_utc(active_package_1["metadata_modified"]).isoformat()
    assert indexed_package_1["organisations"][0]["uuid"] == active_package_1["owner_org"]
    assert indexed_package_1["organisations"][0]["slug"] == active_org_1["name"]
    assert indexed_package_1["organisations"][0]["name"] == active_org_1["title"]

    indexed_package_2 = opensearch_client.get(
        index=f"{opensearch_datasets_name}-{suffix}",
        id=str(active_package_2["id"]),
    )["_source"]
    assert indexed_package_2["title"] == active_package_2["title"]
    assert indexed_package_2["description_raw"] == active_package_2["notes"]
    assert indexed_package_2["created_at"] == _get_utc(active_package_2["metadata_created"]).isoformat()
    assert indexed_package_2["updated_at"] == _get_utc(active_package_2["metadata_modified"]).isoformat()
    assert indexed_package_2["organisations"][0]["uuid"] == active_package_2["owner_org"]
    assert indexed_package_2["organisations"][0]["slug"] == active_org_2["name"]
    assert indexed_package_2["organisations"][0]["name"] == active_org_2["title"]
    with pytest.raises(opensearchpy.exceptions.NotFoundError):
        opensearch_client.get(index=f"{opensearch_datasets_name}-{suffix}", id=str(deleted_package["id"]))


@patch("indexer.utils.get_all_collections")
def test_index_ckan_and_collections_indexed_correctly(
    mock_get_all_collections,
    package_factory,
    collection_factory,
    configured_opensearch_client,
    opensearch_datasets_name,
):
    active_package = package_factory()
    active_collection = collection_factory()
    mock_get_all_collections.return_value = [active_collection]
    opensearch_client = configured_opensearch_client
    suffix = "test"

    opensearch.index_ckan_and_collections(suffix=suffix, row_limit=1)

    indexed_package = opensearch_client.get(index=f"{opensearch_datasets_name}-{suffix}", id=str(active_package["id"]))[
        "_source"
    ]
    assert indexed_package["title"] == active_package["title"]
    assert indexed_package["description_raw"] == active_package["notes"]
    assert indexed_package["created_at"] == active_package["metadata_created"].replace(tzinfo=None).isoformat()
    assert indexed_package["updated_at"] == active_package["metadata_modified"].replace(tzinfo=None).isoformat()
    assert indexed_package["organisations"][0]["uuid"] == active_package["owner_org"]

    indexed_collection = opensearch_client.get(
        index=f"{opensearch_datasets_name}-{suffix}",
        id=str(active_collection["uuid"]),
    )["_source"]
    assert indexed_collection["title"] == active_collection["title"]
    assert indexed_collection["description"] == active_collection["description"]
    assert indexed_collection["created_at"] == active_collection["created_at"]
    assert indexed_collection["updated_at"] == active_collection["updated_at"]


@patch("indexer.utils.get_all_collections")
def test_index_ckan_and_collections_with_no_collections(
    mock_get_all_collections,
    package_factory,
    configured_opensearch_client,
    opensearch_datasets_name,
):
    active_package = package_factory()
    mock_get_all_collections.return_value = []
    opensearch_client = configured_opensearch_client
    suffix = "test"

    opensearch.index_ckan_and_collections(suffix=suffix, row_limit=1)

    indexed_package = opensearch_client.get(index=f"{opensearch_datasets_name}-{suffix}", id=str(active_package["id"]))[
        "_source"
    ]
    assert indexed_package["title"] == active_package["title"]
    assert indexed_package["description_raw"] == active_package["notes"]
    assert indexed_package["created_at"] == active_package["metadata_created"].replace(tzinfo=None).isoformat()
    assert indexed_package["updated_at"] == active_package["metadata_modified"].replace(tzinfo=None).isoformat()
    assert indexed_package["organisations"][0]["uuid"] == active_package["owner_org"]


def test_index_ckan_with_row_limit_package_indexed_correctly(
    package_factory,
    configured_opensearch_client,
    opensearch_datasets_name,
):
    active_package_1, _ = package_factory()
    active_package_2, _ = package_factory()
    opensearch_client = configured_opensearch_client
    suffix = "test"

    opensearch.index_ckan(index_name=f"{opensearch_datasets_name}-{suffix}", row_limit=1)

    indexed_package_1 = opensearch_client.get(
        index=f"{opensearch_datasets_name}-{suffix}",
        id=str(active_package_1["id"]),
    )["_source"]
    assert indexed_package_1["title"] == active_package_1["title"]
    with pytest.raises(opensearchpy.exceptions.NotFoundError):
        opensearch_client.get(index=f"{opensearch_datasets_name}-{suffix}", id=str(active_package_2["id"]))


def test_index_ckan_nothing_indexed_stops_early(package_factory, opensearch_datasets_name):
    package_factory(state="deleted")

    success_count = opensearch.index_ckan(index_name=f"{opensearch_datasets_name}-test")

    assert success_count == 0


@freeze_time("2026-08-28")
def test_clear_opensearch_clears_successfully(
    package_factory,
    configured_opensearch_client,
    opensearch_datasets_name,
    opensearch_datasets_template_name,
):
    package_factory()
    opensearch_client = configured_opensearch_client
    suffix = "2026-08-28t00.00.00+00.00"
    opensearch.index_ckan(index_name=f"{opensearch_datasets_name}-{suffix}")

    expected_index_name = opensearch_datasets_name + f"-{suffix}"
    all_indices = list(opensearch_client.indices.get(index="*").keys())
    assert expected_index_name in all_indices
    all_templates = [template["name"] for template in opensearch_client.indices.get_index_template()["index_templates"]]
    assert opensearch_datasets_template_name in all_templates

    opensearch.clear_opensearch()

    all_indices = list(opensearch_client.indices.get(index="*").keys())
    assert expected_index_name not in all_indices
    all_templates = [template["name"] for template in opensearch_client.indices.get_index_template()["index_templates"]]
    assert opensearch_datasets_template_name not in all_templates
