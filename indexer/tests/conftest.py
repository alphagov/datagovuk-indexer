from unittest.mock import MagicMock

import frontmatter
import psycopg
import pytest
from opensearchpy import OpenSearch

from config import config
from indexer import opensearch

from .factories import create_package


@pytest.fixture(autouse=True)
def override_collections_path(tmp_path):
    old_path = config.COLLECTIONS_PATH
    config.COLLECTIONS_PATH = tmp_path
    yield tmp_path
    config.COLLECTIONS_PATH = old_path


@pytest.fixture
def opensearch_url():
    return config.OPENSEARCH_URL


@pytest.fixture
def opensearch_datasets_name():
    return "datasets-test"


@pytest.fixture
def opensearch_datasets_prefix(opensearch_datasets_name):
    return f"{opensearch_datasets_name}-"


@pytest.fixture
def opensearch_datasets_template_name(opensearch_datasets_prefix):
    return f"{opensearch_datasets_prefix}template"


@pytest.fixture(autouse=True)
def override_opensearch_settings(opensearch_datasets_name):
    # Ensure that our tests all operate on a different opensearch prefix
    config.DATASETS_INDEX["name"] = opensearch_datasets_name
    config.DATASETS_INDEX["priority"] = 101


@pytest.fixture
def clear_opensearch(opensearch_datasets_name, opensearch_datasets_prefix, opensearch_datasets_template_name):
    def _clear(client):
        client.indices.delete(index=f"{opensearch_datasets_prefix}*", ignore=[404])
        client.indices.delete_index_template(name=opensearch_datasets_template_name, ignore=[404])

    return _clear


@pytest.fixture
def opensearch_client(opensearch_url, clear_opensearch):
    client = OpenSearch(hosts=[config.OPENSEARCH_URL])

    clear_opensearch(client)
    yield client
    clear_opensearch(client)


@pytest.fixture
def configured_opensearch_client(opensearch_client):
    opensearch.setup_index()
    return opensearch_client


@pytest.fixture
def postgres_dsn():
    return config.POSTGRES_DSN + "-test"


@pytest.fixture(autouse=True)
def override_postgres_settings(postgres_dsn, ckan_connection):
    # Ensure that our tests all operate on a test postgres DB
    old_dsn = config.POSTGRES_DSN
    config.POSTGRES_DSN = postgres_dsn
    yield
    config.POSTGRES_DSN = old_dsn
    cursor = ckan_connection.cursor()
    cursor.execute("TRUNCATE TABLE package;")
    cursor.execute('TRUNCATE TABLE "group";')


@pytest.fixture
def ckan_connection(postgres_dsn):
    connection = psycopg.connect(postgres_dsn, autocommit=True)
    yield connection
    connection.close()


@pytest.fixture
def package_factory(ckan_connection):
    def _create(**kwargs):
        return create_package(ckan_connection, **kwargs)

    return _create


@pytest.fixture
def collection_factory(override_collections_path):
    test_collection_markdown = override_collections_path / "test-collection.md"
    test_collection_markdown.write_text(
        "---\n"
        "uuid: 00000000-0000-0000-0000-000000000001\n"
        "title: Test Collection\n"
        "created_at: '2026-01-01T00:00:00'\n"
        "updated_at: '2026-01-01T00:00:00'\n"
        "organisations:\n"
        "---\n"
        "This is **test** content.\n",
    )
    return frontmatter.load(test_collection_markdown)


@pytest.fixture
def collections_with_topics():
    return [
        {
            "name": "collection-name",
            "topics": [
                {
                    "slug": "test-topic",
                    "title": "test topic",
                    "description": "Test description",
                    "description_raw": "test \ndescription\n",
                    "page-last-updated": "2026-08-28T00:00:00Z",
                },
            ],
        },
    ]


@pytest.fixture
def failing_bulk_index(monkeypatch):
    async def _failing_bulk_index(*args, **kwargs):
        yield False, {"error": "something went wrong"}

    monkeypatch.setattr(opensearch.helpers, "async_streaming_bulk", _failing_bulk_index)


@pytest.fixture
def mock_bulk_with_error(monkeypatch):
    mock = MagicMock(return_value=(0, ["some error"]))
    monkeypatch.setattr(opensearch.helpers, "bulk", mock)
    return mock
