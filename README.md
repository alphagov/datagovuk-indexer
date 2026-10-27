# datagovuk-indexer

data.gov.uk opensearch indexer.


## Running locally

The following steps will explain how to run the application locally and get in to a state where pull requests can be opened to modify the project on github.
They assume a user using Mac OSX.

### Install docker desktop
https://docs.docker.com/desktop/setup/install/mac-install/

### Install justfile
`just` is a simple way to save/run project-specific commands.  It's an alternative to `make` and the devs go in to the differences on the project homepage; https://github.com/casey/just

```
brew install just
```

### Initialise with justfile

```
just init
```

### Bring up the project under docker

`just up`

The docker containers should now all be running.

Go to http://localhost:5601/ - you should see a dashboard for opensearch.
`just shell` starts a python shell on the indexer container.

### Indexing CKAN datasets to opensearch

You will need a DB dump from S3.  On the ndl-integration account, go to the web console.
- go to S3
- integration-account-ckan-backup
- ckan-postgres

Download the latest backup `.gz` file.

```
just load-db <path_to_db_dump.gz>
```

Note this is likely to take around 1H or so.

Now that we have a ckan postgres instance running and populated, we can index the data in to opensearch;

```
just index
```

This will take a few seconds.

The data should now be browsable on the opensearch dashboard, in a browser do the follwing steps;

- Go to the opensearch dashboard; http://localhost:5601/app/management/opensearch-dashboards/indexPatterns
- Click "Create index pattern"
- Enter "datasets-*" as the index pattern name and create the pattern
- Go to http://localhost:5601/app/data-explorer/discover - you should see opensearch documents for all datasets!


## Publishing a pre-populated opensearch image

We publish an opensearch image to GHCR which already contains a small, mostly stable set of data:

- the first 1000 active ckan datasets created on or after 2024-01-01 (oldest first)
- all datagovuk collections

This lets other projects run against realistic search data without loading a ckan DB dump or running the indexer.
The image is built on demand, using the `seed-*` justfile recipes.

### Prerequisites

- A populated ckan postgres DB (see [Indexing CKAN datasets to opensearch](#indexing-ckan-datasets-to-opensearch))
- The datagovuk django app running on the `datagovuk` docker network, so that `http://django:8000/collections.json` is reachable.
  To use another source for collections, override the URL, e.g. `just seed_datagovuk_url=<url> seed-build`
- To publish: the `gh` CLI with the `write:packages` scope (`gh auth refresh -s write:packages`)

### Build and check the image locally

```
just seed-build
```

This starts a throwaway opensearch node (the `opensearch-seed` compose service) and indexes the data in to it.
It then stops the node, copies its data to `build/opensearch-seed/data` and builds `ghcr.io/alphagov/datagovuk-indexer-opensearch:latest`.

To check the image:

```
docker run --rm -p 9201:9200 ghcr.io/alphagov/datagovuk-indexer-opensearch:latest
curl 'localhost:9201/datasets/_count?q=source:ckan'
```

### Publish to GHCR

`seed-publish` pushes the data from the last `seed-build`, tagged with the given tag and `latest`, for both amd64 and arm64:

```
just ghcr-login
just seed-publish 2026-10-27
```

The first time the image is published, its package will be private.
Change its visibility in the package settings on GitHub if it should be public.

`just seed-clean` removes the seed container and the copied data.

### Using the image

```
docker run -p 9200:9200 ghcr.io/alphagov/datagovuk-indexer-opensearch:latest
```

The data is served from the `datasets` alias.
The image runs as a single node with security disabled; it is intended for local development and testing only.


## Basic Commands

### Running tests with pytest

`just test` - runs the tests under docker

### View docker stack logs

`just logs`

### Rebuild the docker stack

`just build`

### Other common commands

`just` should list out other common commands in the project
