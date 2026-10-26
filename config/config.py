from uuid import UUID

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

RDS_ENDPOINT = env("RDS_ENDPOINT", default=None)
DB_USER = env("DB_USER", default=None)
DB_NAME = env("DB_NAME", default="ckan")
AWS_REGION = env("AWS_REGION", default="eu-west-2")

NAMESPACE_UUID = UUID("4f8407d1-1c14-46ee-a858-36b40467aa7f")
DATAGOVUK_URL = env("DATAGOVUK_URL", default="https://data.gov.uk")
