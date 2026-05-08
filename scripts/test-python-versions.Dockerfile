ARG PYTHON_VERSION=3.13
FROM ghcr.io/astral-sh/uv:python${PYTHON_VERSION}-trixie-slim

LABEL org.opencontainers.image.title=pystrich-test

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv

RUN apt-get update \
 && apt-get install -y --no-install-recommends dmtx-utils zbar-tools imagemagick librsvg2-bin ghostscript \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /src

# Install dependencies first so the layer can be cached across source edits.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-install-project --group dev

COPY . .
RUN uv sync --frozen --group dev

CMD ["uv", "run", "--frozen", "pytest"]
