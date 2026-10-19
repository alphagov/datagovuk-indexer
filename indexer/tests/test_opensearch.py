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


def test_setup_index_adds_index_template_successfully(opensearch_datasets_template_name, opensearch_client):
    opensearch.setup_index()
    templates = opensearch_client.indices.get_index_template(name=opensearch_datasets_template_name)
    assert templates["index_templates"][0]["name"] == opensearch_datasets_template_name
    assert (
        templates["index_templates"][0]["index_template"]["template"]["mappings"]["properties"]["uuid"]["type"]
        == "keyword"
    )


def _get_utc(dt):
    return dt.replace(tzinfo=None)


def test_index_opensearch_correctly(
    collection_factory,
    package_factory,
    configured_opensearch_client,
    opensearch_datasets_name,
):
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
    assert indexed_package_1["source"] == "ckan"
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
    assert indexed_package_2["source"] == "ckan"
    assert indexed_package_2["description_raw"] == package_2["notes"]
    assert indexed_package_2["created_at"] == _get_utc(package_2["metadata_created"]).isoformat()
    assert indexed_package_2["updated_at"] == _get_utc(package_2["metadata_modified"]).isoformat()
    assert indexed_package_2["organisations"][0]["uuid"] == package_2["owner_org"]
    assert indexed_package_2["organisations"][0]["slug"] == org_2["name"]
    assert indexed_package_2["organisations"][0]["name"] == org_2["title"]

    indexed_collection = opensearch_client.get(
        index=f"{opensearch_datasets_name}",
        id=str(collection_factory["uuid"]),
    )["_source"]
    assert indexed_collection["title"] == collection_factory["title"]
    assert indexed_collection["source"] == "collection"
    assert indexed_collection["description"] == "This is test content."
    assert indexed_collection["description_raw"] == collection_factory.content
    assert indexed_collection["organisations"] == collection_factory["organisations"]
    assert indexed_collection["created_at"] == collection_factory["created_at"]
    assert indexed_collection["updated_at"] == collection_factory["updated_at"]


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
    configured_opensearch_client,
    opensearch_datasets_name,
):
    opensearch_client = configured_opensearch_client
    result = opensearch.index_opensearch()

    assert result is False
    with pytest.raises(opensearchpy.exceptions.NotFoundError):
        opensearch_client.get(index=f"{opensearch_datasets_name}", id="nonexistent")


def test_index_opensearch_fails_if_no_collections(
    package_factory,
    configured_opensearch_client,
):
    package_factory()
    result = opensearch.index_opensearch()
    assert result is False


def test_index_opensearch_fails_if_no_ckan(
    collection_factory,
    configured_opensearch_client,
):
    result = opensearch.index_opensearch()
    assert result is False


def test_index_opensearch_alias_moves_on_reindex(
    collection_factory,
    package_factory,
    configured_opensearch_client,
    opensearch_datasets_name,
):
    package_factory()
    opensearch_client = configured_opensearch_client

    with freeze_time("2026-08-28"):
        opensearch.index_opensearch()
    first_aliases = opensearch_client.indices.get_alias(name=opensearch_datasets_name)
    first_index = next(iter(first_aliases.keys()))

    package_factory()
    with freeze_time("2026-08-29"):
        opensearch.index_opensearch()
    second_aliases = opensearch_client.indices.get_alias(name=opensearch_datasets_name)
    second_index = next(iter(second_aliases.keys()))

    assert first_index == f"{opensearch_datasets_name}-2026-08-28t00.00.00+00.00"
    assert second_index == f"{opensearch_datasets_name}-2026-08-29t00.00.00+00.00"
    aliases = opensearch_client.indices.get_alias(index=first_index)
    assert opensearch_datasets_name not in aliases[first_index]["aliases"]


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


@freeze_time("2026-08-28")
def test_clear_opensearch_clears_successfully(
    collection_factory,
    package_factory,
    configured_opensearch_client,
    opensearch_datasets_name,
    opensearch_datasets_template_name,
):
    package_factory()
    opensearch_client = configured_opensearch_client
    opensearch.index_opensearch()

    expected_index_name = opensearch_datasets_name + "-2026-08-28t00.00.00+00.00"
    all_indices = list(opensearch_client.indices.get(index="*").keys())
    assert expected_index_name in all_indices
    all_templates = [template["name"] for template in opensearch_client.indices.get_index_template()["index_templates"]]
    assert opensearch_datasets_template_name in all_templates

    opensearch.clear_opensearch()

    all_indices = list(opensearch_client.indices.get(index="*").keys())
    assert expected_index_name not in all_indices
    all_templates = [template["name"] for template in opensearch_client.indices.get_index_template()["index_templates"]]
    assert opensearch_datasets_template_name not in all_templates


def test_transform_context_transforms_nested_list():
    result = opensearch.transform_context({"test-key": ["test1", "test2"]})
    assert result == {"test_key": ["test1", "test2"]}


def test_index_collections_logs_warning_on_errors(mock_bulk_with_error, caplog, collection_factory):
    opensearch.index_collections(index_name="datasets-test-2026-01-01t00.00.00+00.00")
    assert "Failed to index 1 collection documents due to errors" in caplog.text


def test_index_ckan_logs_warning_on_failure(failing_bulk_index, caplog, package_factory):
    package_factory()
    result = opensearch.index_ckan(index_name="datasets-test-2026-01-01t00.00.00+00.00")
    assert result == 0
    assert "Failed to index document" in caplog.text
