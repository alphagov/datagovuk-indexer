"""Postgres connections to the CKAN database.
In AWS, terraform outputs the RDS endpoint as host:port only, no scheme,
user or password
"""

import boto3
import psycopg

from config import config


def _iam_token(host, port, user, region):
    return boto3.client("rds", region_name=region).generate_db_auth_token(
        DBHostname=host,
        Port=port,
        DBUsername=user,
    )


def rds_connection_info(endpoint, user, dbname, region):
    host, _, port = endpoint.partition(":")
    port = int(port or 5432)
    return {
        "host": host,
        "port": port,
        "user": user,
        "dbname": dbname,
        "password": _iam_token(host, port, user, region),
        "sslmode": "require",
    }


async def connect(**kwargs):
    if config.RDS_ENDPOINT:
        return await psycopg.AsyncConnection.connect(
            **rds_connection_info(config.RDS_ENDPOINT, config.DB_USER, config.DB_NAME, config.AWS_REGION),
            **kwargs,
        )
    if config.POSTGRES_DSN:
        return await psycopg.AsyncConnection.connect(config.POSTGRES_DSN, **kwargs)
    message = "Database is not configured. Set RDS_ENDPOINT (IAM auth) or POSTGRES_DSN (local) to enable it."
    raise RuntimeError(message)
