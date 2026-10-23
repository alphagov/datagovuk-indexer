import httpx

from config import config


def get_datagovuk_collections() -> list:
    with httpx.Client() as client:
        try:
            response = client.get(f"{config.DATAGOVUK_URL}/collections.json")
            response.raise_for_status()
            return response.json().get("result", [])
        except httpx.HTTPError:
            return []
