export COMPOSE_FILE := "docker-compose.local.yml"


# Default command to list all available commands.
default:
    @just --list

# init: Initialise core dependencies for working on datagovuk-indexer
init:
    @echo "Installing uv..."
    brew install uv
    @echo ""
    @echo "Installing pre-commit..."
    uv tool install pre-commit --with pre-commit-uv
    @echo ""
    @echo "Initialising pre-commit..."
    pre-commit install
    @echo ""
    @echo "Copying overrides envfile if target does not exist..."
    @test -f .envs/.local-overrides || cp .envs/.local-overrides.example .envs/.local-overrides
    @echo ""
    @echo "Installing libpq..."
    brew install libpq
    @echo ""
    @echo "datagovuk-indexer install is initialised for local development. Bringing up the containers with '$ just up'"
    just up

# load-db: Load a postgres dump image in to the docker container
load-db +args:
    psql "postgresql://postgres:postgres_password@127.0.0.1:5432/ckan" -c "CREATE EXTENSION IF NOT EXISTS postgis;"
    @echo "Loading ckan backup file...  This could take a while (~1 hour+)"
    pg_restore -d "postgresql://postgres:postgres_password@127.0.0.1:5432/ckan" -j 8 --no-owner --no-privileges {{args}}

# build: Build python image.
build *args:
    @echo "Building docker-compose stack..."
    docker compose -f docker-compose.local.yml build {{args}}

# up: Start up containers.
up *args:
    @echo "Starting up containers..."
    docker compose -f docker-compose.local.yml up -d --remove-orphans {{args}}

# restart: Restart containers
restart *args:
    @echo "Restarting containers..."
    docker compose -f docker-compose.local.yml restart

# down: Stop containers.
down  *args:
    @echo "Stopping containers..."
    @docker compose down {{args}}

# prune: Remove containers and their volumes.
prune *args:
    @echo "Killing containers and removing volumes..."
    @docker compose down -v {{args}}

# logs: View container logs
logs *args:
    @docker compose logs -f {{args}}

# shell: Get a python shell on indexer
shell:
    @docker compose run --rm indexer python

# dbshell: Get a psql shell on ckan DB
dbshell:
    psql "postgresql://postgres:postgres_password@127.0.0.1:5432/ckan"

# bash: Get a bash shell on indexer
bash:
    @docker compose run --rm indexer bash

# index: Index ckan postgres DB to opensearch
index *args:
    @docker compose run --rm indexer uv run python indexer/cli.py index {{args}}

# opensearch-clear: Clean opensearch indeces, templates, aliases
clear:
    @docker compose run --rm indexer uv run python indexer/cli.py clear

# dump-ckan-schema: Dump ckan's schema in to a local SQL file
dump-ckan-schema:
    pg_dump --dbname="postgresql://postgres:postgres_password@127.0.0.1:5432/ckan" --schema-only > ckan_schema.sql

# run: Executes docker compose run command
run +args:
    @docker compose run --rm {{args}}

# test: Run pytest
test *args:
    @docker compose exec indexer pytest {{args}}

# coverage: Run python coverage
coverage:
    @docker compose exec indexer coverage run -m pytest
    @docker compose exec indexer coverage html

# lint: Run pre-commit checks without the commit
lint *args:
    pre-commit run {{args}}

# Build production docker image
prod-build *args:
    @echo "Building production python image..."
    docker compose -f docker-compose.production.yml build {{args}}

# Bring up production docker container
prod-up *args:
    @echo "Starting up production containers..."
    docker compose -f docker-compose.production.yml up -d --remove-orphans {{args}}

# Bring down production docker container
prod-down *args:
    @echo "Stopping production containers..."
    docker compose -f docker-compose.production.yml down {{args}}
