from logging import getLogger

from opensearchpy import OpenSearch

from config import config

logger = getLogger(__file__)


class BadlyConfiguredError(Exception):
    pass


def get_client():
    if not config.OPENSEARCH_URL:
        message = "Missing OPENSEARCH_URL config variable"
        raise BadlyConfiguredError(message)
    return OpenSearch(hosts=[config.OPENSEARCH_URL])


def configure_mappings():
    datasets_prefix = f"{config.DATASETS_INDEX['name']}-"
    datasets_template = {
        "index_patterns": [f"{datasets_prefix}*"],
        "template": {
            "settings": {
                "number_of_shards": config.DATASETS_INDEX["settings"]["number_of_shards"],
                "number_of_replicas": config.DATASETS_INDEX["settings"]["number_of_replicas"],
                "analysis": {
                    "normalizer": {
                        "lowercase_normalizer": {
                            "type": "custom",
                            "filter": ["lowercase"],
                        },
                    },
                },
            },
            "mappings": {
                "properties": {
                    "uuid": {"type": "keyword"},
                    "title": {
                        "type": "text",
                        "fields": {
                            "keyword": {"type": "keyword", "ignore_above": 256},
                            "english": {"type": "text", "analyzer": "english"},
                        },
                    },
                },
            },
        },
        "priority": config.DATASETS_INDEX["priority"],
    }

    client = get_client()
    template_name = f"{datasets_prefix}template"
    client.indices.put_index_template(name=template_name, body=datasets_template)
    logger.info("Index template '%s' configured.", template_name)
