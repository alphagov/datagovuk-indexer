from datetime import UTC, datetime

from factory import DictFactory, Faker, LazyAttribute, LazyFunction, SubFactory
from psycopg import sql


class OrganisationFactory(DictFactory):
    class Meta:
        model = dict

    id = Faker("uuid4")
    name = Faker("slug")
    title = Faker("catch_phrase")
    description = Faker("catch_phrase")
    created = LazyFunction(lambda: datetime.now(tz=UTC))
    state = "active"
    type = "organization"
    approval_status = "pending"
    image_url = ""
    is_organization = True


class PackageFactory(DictFactory):
    class Meta:
        model = dict

    class Params:
        org = SubFactory(OrganisationFactory)

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
    private = False
    metadata_modified = LazyFunction(lambda: datetime.now(tz=UTC))
    creator_user_id = Faker("uuid4")
    metadata_created = LazyFunction(lambda: datetime.now(tz=UTC))
    owner_org = LazyAttribute(lambda o: o.org["id"])


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
    organisation = OrganisationFactory()
    package = PackageFactory(**kwargs, org=organisation)
    cursor = ckan_connection.cursor()
    insert_postgres_row(cursor=cursor, data=organisation, table_name="group")
    insert_postgres_row(cursor=cursor, data=package, table_name="package")
    return package, organisation
