import environ

env = environ.Env()

OPENSEARCH_URL = env("OPENSEARCH_URL", default=None)
DATASETS_INDEX = {
    "name": "datasets",
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 1,
    },
    "priority": 100,
}

POSTGRES_DSN = env("POSTGRES_DSN", default=None)
POSTGRES_BATCH_SIZE = 2000
