import psycopg
import pytest
from opensearchpy import OpenSearch

from config import config
from indexer import opensearch

from .factories import create_package


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
def clear_opensearch(opensearch_datasets_prefix, opensearch_datasets_template_name):
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
    opensearch.configure_mappings()
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


@pytest.fixture
def ckan_connection(postgres_dsn):
    connection = psycopg.connect(postgres_dsn, autocommit=True)
    yield connection
    connection.close()


@pytest.fixture
def package_factory(ckan_connection):
    def _create(**kwargs):
        package = create_package(ckan_connection, **kwargs)
        return package

    return _create
