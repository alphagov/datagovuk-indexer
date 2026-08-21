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

### Environment variables

TODO...


## Basic Commands

### Running tests with pytest

`just test` - runs the tests under docker

### View docker stack logs

`just logs`

### Rebuild the docker stack

`just build`

### Other common commands

`just` should list out other common commands in the project
