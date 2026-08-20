export COMPOSE_FILE := "docker-compose.local.yml"


# Default command to list all available commands.
default:
    @just --list

# init: Initialise core dependencies for working on datagovuk-indexer
init:
    @echo "not implemented..."

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

bash:
    echo "not implemented..."

# run: Executes docker compose run command
run +args:
    @docker compose run --rm {{args}}

# test: Run pytest
test *args:
    echo "not implemented..."

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
