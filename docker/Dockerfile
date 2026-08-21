FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS python-build-stage

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0

ARG APP_HOME=/app

WORKDIR ${APP_HOME}

RUN apt-get update && apt-get install --no-install-recommends -y \
  build-essential

COPY pyproject.toml ${APP_HOME}
COPY uv.lock ${APP_HOME}

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev
COPY . ${APP_HOME}

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

RUN addgroup --system indexer \
  && adduser --system --ingroup indexer indexer

# make indexer owner of the WORKDIR directory as well.
RUN chown indexer:indexer ${APP_HOME}

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"


FROM python-build-stage AS python-run-production

ENTRYPOINT ["echo", "'TODO'"]


FROM python-build-stage AS python-run-dev

# we need to move the virtualenv outside of the $APP_HOME directory because it will be overriden by the docker compose mount
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0
ENV VIRTUAL_ENV=/opt/venv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
RUN uv venv $VIRTUAL_ENV

# devcontainer dependencies and utils
RUN apt-get update && apt-get install --no-install-recommends -y \
  sudo git bash-completion nano ssh

# Create devcontainer user and add it to sudoers
RUN groupadd --gid 1000 dev-user \
  && useradd --uid 1000 --gid dev-user --shell /bin/bash --create-home dev-user \
  && echo dev-user ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/dev-user \
  && chmod 0440 /etc/sudoers.d/dev-user

COPY --from=python-build-stage ${APP_HOME}/.venv ${VIRTUAL_ENV}
# Requirements are installed here to ensure they will be cached.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync

ENV PATH="/${VIRTUAL_ENV}/bin:$PATH"
ENV PYTHONPATH="${VIRTUAL_ENV}/lib/python3.14/site-packages"
