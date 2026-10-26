from unittest.mock import MagicMock, patch

import requests

from config import config
from indexer import datagovuk


@patch("indexer.datagovuk.requests.get")
def test_get_datagovuk_collections_returns_collections(mock_get, collections_with_topics):
    mock_response = MagicMock()
    mock_response.json.return_value = {"collections": collections_with_topics}
    mock_get.return_value = mock_response

    result = datagovuk.get_datagovuk_collections()

    assert result == collections_with_topics
    mock_get.assert_called_once_with(f"{config.DATAGOVUK_URL}/collections.json", timeout=30)


@patch("indexer.datagovuk.requests.get")
def test_get_datagovuk_collections_missing_collections_key_returns_empty_list(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {}
    mock_get.return_value = mock_response

    result = datagovuk.get_datagovuk_collections()

    assert result == []


@patch("indexer.datagovuk.requests.get")
def test_get_datagovuk_collections_returns_empty_list_on_error_status(mock_get):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.HTTPError("500 Server Error")
    mock_get.return_value = mock_response

    result = datagovuk.get_datagovuk_collections()

    assert result == []


@patch("indexer.datagovuk.requests.get")
def test_get_datagovuk_collections_returns_empty_list_on_request_error(mock_get):
    mock_get.side_effect = requests.ConnectionError("Connection refused")

    result = datagovuk.get_datagovuk_collections()

    assert result == []
