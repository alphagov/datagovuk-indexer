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


def test_index_ckan_active_packages_indexed_correctly(
    package_factory,
    configured_opensearch_client,
    opensearch_datasets_name,
):
    active_package_1 = package_factory()
    active_package_2 = package_factory()
    deleted_package = package_factory(state="deleted")
    opensearch_client = configured_opensearch_client

    opensearch.index_ckan()

    indexed_package_1 = opensearch_client.get(index=opensearch_datasets_name, id=str(active_package_1["id"]))["_source"]
    assert indexed_package_1["title"] == active_package_1["title"]
    indexed_package_2 = opensearch_client.get(index=opensearch_datasets_name, id=str(active_package_2["id"]))["_source"]
    assert indexed_package_2["title"] == active_package_2["title"]
    with pytest.raises(opensearchpy.exceptions.NotFoundError):
        opensearch_client.get(index=opensearch_datasets_name, id=str(deleted_package["id"]))


def test_index_ckan_with_row_limit_package_indexed_correctly(
    package_factory,
    configured_opensearch_client,
    opensearch_datasets_name,
):
    active_package_1 = package_factory()
    active_package_2 = package_factory()
    opensearch_client = configured_opensearch_client

    opensearch.index_ckan(row_limit=1)

    indexed_package_1 = opensearch_client.get(index=opensearch_datasets_name, id=str(active_package_1["id"]))["_source"]
    assert indexed_package_1["title"] == active_package_1["title"]
    with pytest.raises(opensearchpy.exceptions.NotFoundError):
        opensearch_client.get(index=opensearch_datasets_name, id=str(active_package_2["id"]))


def test_index_ckan_nothing_indexed_stops_early(package_factory):
    package_factory(state="deleted")

    success_count = opensearch.index_ckan()

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
    opensearch.index_ckan()

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
