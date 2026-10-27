export COMPOSE_FILE := "docker-compose.local.yml"

# Pre-populated opensearch image settings (see the seed-* recipes)
seed_image := "ghcr.io/alphagov/datagovuk-indexer-opensearch"
seed_datagovuk_url := "http://django:8000"
seed_platforms := "linux/amd64,linux/arm64"
seed_build_dir := "build/opensearch-seed"


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
    docker network create datagovuk || true
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

# seed-index: Index a sample of ckan datasets and all collections in to a throwaway opensearch node
seed-index:
    @echo "Starting a fresh seed opensearch node..."
    docker compose --profile seed rm -sf opensearch-seed
    docker compose --profile seed up -d --wait opensearch-seed
    docker compose run --rm \
        -e OPENSEARCH_URL=http://opensearch-seed:9200 \
        -e DATAGOVUK_URL={{seed_datagovuk_url}} \
        indexer uv run python indexer/cli.py index
    @echo "Preparing index for a single node image..."
    docker compose --profile seed exec -T opensearch-seed curl -sf -XPUT 'localhost:9200/datasets-*/_settings' \
        -H 'Content-Type: application/json' -d '{"index": {"number_of_replicas": 0}}'
    @echo ""
    docker compose --profile seed exec -T opensearch-seed curl -sf -XPOST 'localhost:9200/_flush'
    @echo ""
    @echo "Indexed document counts:"
    docker compose --profile seed exec -T opensearch-seed curl -sf 'localhost:9200/datasets/_count?q=source:ckan'
    @echo ""
    docker compose --profile seed exec -T opensearch-seed curl -sf 'localhost:9200/datasets/_count?q=source:collection'
    @echo ""

# seed-build: Build the pre-populated opensearch image locally
seed-build tag="latest": seed-index
    @echo "Stopping seed opensearch node and copying its data..."
    docker compose --profile seed stop opensearch-seed
    rm -rf {{seed_build_dir}}
    mkdir -p {{seed_build_dir}}
    docker cp opensearch_seed:/usr/share/opensearch/data {{seed_build_dir}}/data
    docker compose --profile seed rm -f opensearch-seed
    @echo "Building {{seed_image}}:{{tag}}..."
    docker buildx build --load -f docker/opensearch-seed/Dockerfile -t {{seed_image}}:{{tag}} {{seed_build_dir}}

# seed-publish: Push the pre-populated opensearch image built by seed-build to GHCR, e.g. `just seed-publish 2026-10-27`
seed-publish tag:
    @test -d {{seed_build_dir}}/data || (echo "No seed data found in {{seed_build_dir}}; run 'just seed-build' first." && exit 1)
    @echo "Publishing {{seed_image}}:{{tag}} and {{seed_image}}:latest for {{seed_platforms}}..."
    docker buildx build --push --platform {{seed_platforms}} -f docker/opensearch-seed/Dockerfile \
        -t {{seed_image}}:{{tag}} -t {{seed_image}}:latest {{seed_build_dir}}

# seed-clean: Remove the seed opensearch node and copied seed data
seed-clean:
    docker compose --profile seed rm -sf opensearch-seed
    rm -rf {{seed_build_dir}}

# ghcr-login: Log docker in to GHCR using the gh CLI (needs `gh auth refresh -s write:packages`)
ghcr-login:
    SSL_CERT_FILE= gh auth token | SSL_CERT_FILE= docker login ghcr.io -u "$(SSL_CERT_FILE= gh api user -q .login)" --password-stdin
