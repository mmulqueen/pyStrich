ARG PYTHON_VERSION=3.13
# uv binary, pulled from the upstream image so we don't curl-install at build time.
FROM ghcr.io/astral-sh/uv:0.9 AS uv

FROM ubuntu:24.04

COPY --from=uv /uv /uvx /usr/local/bin/

LABEL org.opencontainers.image.title=pystrich-test

ARG PYTHON_VERSION
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON=${PYTHON_VERSION} \
    DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        ca-certificates dmtx-utils zbar-tools imagemagick librsvg2-bin ghostscript \
 && rm -rf /var/lib/apt/lists/*

RUN uv python install ${PYTHON_VERSION}

WORKDIR /src

# Install dependencies first so the layer can be cached across source edits.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-install-project --group dev

COPY . .
RUN uv sync --frozen --group dev

CMD ["uv", "run", "--frozen", "pytest"]