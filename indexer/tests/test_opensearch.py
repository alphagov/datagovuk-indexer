import pytest

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
