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


## Basic Commands

### Running tests with pytest

`just test` - runs the tests under docker

### View docker stack logs

`just logs`

### Rebuild the docker stack

`just build`

### Other common commands

`just` should list out other common commands in the project
