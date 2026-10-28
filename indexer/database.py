import boto3
import psycopg

from config import config


class DatabaseNotConfiguredError(Exception):
    pass


def create_aws_rds_token(host, port):
    # Tokens expire after 15 minutes. We only need this for creating a connection.
    client = boto3.client("rds", region_name=config.AWS_REGION)
    return client.generate_db_auth_token(DBHostname=host, Port=port, DBUsername=config.AWS_RDS_USER)


def aws_rds_connection_info():
    host, _, port = config.AWS_RDS_ENDPOINT.partition(":")
    port = int(port or config.AWS_RDS_PORT)
    temporary_token = create_aws_rds_token(host, port)
    return {
        "host": host,
        "port": port,
        "user": config.AWS_RDS_USER,
        "dbname": config.AWS_RDS_NAME,
        "password": temporary_token,
        "sslmode": "require",
    }


def database_connection_info():
    if config.AWS_RDS_ENDPOINT:
        return aws_rds_connection_info()
    if config.POSTGRES_DSN:
        return {"conninfo": config.POSTGRES_DSN}
    message = "Database is not configured."
    raise DatabaseNotConfiguredError(message)


async def connect(**kwargs):
    return await psycopg.AsyncConnection.connect(**database_connection_info(), **kwargs)
