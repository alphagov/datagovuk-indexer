from datetime import UTC, datetime

from factory import DictFactory, Faker, LazyFunction
from psycopg import sql


class PackageFactory(DictFactory):
    class Meta:
        model = dict

    id = Faker("uuid4")
    name = Faker("slug")
    title = Faker("catch_phrase")
    version = Faker("random_int", min=0, max=999)
    url = Faker("url")
    author = Faker("name")
    author_email = Faker("email")
    maintainer = Faker("name")
    maintainer_email = Faker("email")
    notes = Faker("catch_phrase")
    license_id = Faker("word")
    state = "active"
    type = "dataset"
    owner_org = Faker("word")
    private = False
    metadata_modified = LazyFunction(lambda: datetime.now(tz=UTC))
    creator_user_id = Faker("uuid4")
    metadata_created = LazyFunction(lambda: datetime.now(tz=UTC))


def insert_postgres_row(cursor, data, table_name):
    columns = data.keys()
    values = list(data.values())

    query = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
        sql.Identifier(table_name),
        sql.SQL(", ").join(map(sql.Identifier, columns)),
        sql.SQL(", ").join(sql.Placeholder() for _ in values),
    )

    cursor.execute(query, values)


def create_package(ckan_connection, **kwargs):
    package = PackageFactory(**kwargs)
    cursor = ckan_connection.cursor()
    insert_postgres_row(cursor=cursor, data=package, table_name="package")
    return package
