from unittest.mock import patch

import pytest

from config import config
from indexer import database


@pytest.fixture
def rds_config(monkeypatch):
    monkeypatch.setattr(config, "AWS_RDS_USER", "indexer")
    monkeypatch.setattr(config, "AWS_RDS_NAME", "ckan")


@patch("indexer.database.create_aws_rds_token", return_value="iam-token")
def test_rds_connection_info_parses_endpoint(mock_rds_token, rds_config, monkeypatch):
    monkeypatch.setattr(config, "AWS_RDS_ENDPOINT", "db.example.com:6543")

    assert database.aws_rds_connection_info() == {
        "host": "db.example.com",
        "port": 6543,
        "user": "indexer",
        "dbname": "ckan",
        "password": "iam-token",
        "sslmode": "require",
    }
    mock_rds_token.assert_called_once_with("db.example.com", 6543)


@patch("indexer.database.create_aws_rds_token", return_value="iam-token")
def test_database_connection_info_prefers_rds(mock_rds_token, rds_config, monkeypatch):
    monkeypatch.setattr(config, "AWS_RDS_ENDPOINT", "db.example.com:5432")
    monkeypatch.setattr(config, "POSTGRES_DSN", "postgresql://postgres:password@localhost:5432/ckan")

    assert database.database_connection_info()["host"] == "db.example.com"


def test_database_connection_info_locally_uses_postgres_dsn(monkeypatch):
    monkeypatch.setattr(config, "AWS_RDS_ENDPOINT", None)
    monkeypatch.setattr(config, "POSTGRES_DSN", "postgresql://postgres:password@localhost:5432/ckan")

    assert database.database_connection_info() == {"conninfo": "postgresql://postgres:password@localhost:5432/ckan"}


@pytest.mark.asyncio
async def test_connect_raises_when_not_configured(monkeypatch):
    monkeypatch.setattr(config, "AWS_RDS_ENDPOINT", None)
    monkeypatch.setattr(config, "POSTGRES_DSN", None)

    with pytest.raises(database.DatabaseNotConfiguredError):
        await database.connect()
