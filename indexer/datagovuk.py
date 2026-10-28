import requests

from config import config


def get_datagovuk_collections() -> list:
    response = requests.get(f"{config.DATAGOVUK_URL}/collections.json", timeout=30)
    response.raise_for_status()
    return response.json().get("collections", [])
