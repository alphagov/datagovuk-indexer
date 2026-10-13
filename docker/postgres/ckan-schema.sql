/*
    A subset of ckan's full postgres schema; used purely for creating a test
    database for the purposes of our unit/integration tests where we need to create
    data in ckan and ingest it in to opensearch using the ingestion script.
*/

CREATE TABLE public."group" (
    id text NOT NULL,
    name text NOT NULL,
    title text,
    description text,
    created timestamp without time zone,
    state text,
    type text NOT NULL,
    approval_status text,
    image_url text,
    is_organization boolean DEFAULT false
);

CREATE TABLE public.package (
    id text NOT NULL,
    name character varying(100) NOT NULL,
    title text,
    version character varying(100),
    url text,
    author text,
    author_email text,
    maintainer text,
    maintainer_email text,
    notes text,
    license_id text,
    state text,
    type text,
    owner_org text,
    private boolean DEFAULT false,
    metadata_modified timestamp without time zone,
    creator_user_id text,
    metadata_created timestamp without time zone,
    plugin_data jsonb
);
