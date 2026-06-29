FROM ghcr.io/astral-sh/uv:python3.13-trixie-slim AS build

LABEL org.opencontainers.image.title=pystrich-docs

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /src

COPY pyproject.toml uv.lock README.md ./
# The docs build generates PNG example figures, which need Pillow (the png extra).
RUN uv sync --frozen --no-install-project --no-default-groups --group docs --extra png

COPY . .
RUN uv sync --frozen --no-default-groups --group docs --extra png

RUN uv run --frozen sphinx-build -W --keep-going -b doctest docs docs/_build/doctest
RUN uv run --frozen sphinx-build -W --keep-going -b text docs docs/_build/text
RUN uv run --frozen sphinx-build -W --keep-going -b html docs docs/_build/html

FROM scratch AS export
COPY --from=build /src/docs/_build/html /html
COPY --from=build /src/docs/_build/text /text