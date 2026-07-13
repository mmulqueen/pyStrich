FROM ghcr.io/astral-sh/uv:python3.13-trixie-slim AS build

LABEL org.opencontainers.image.title=pystrich-docs

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /src

COPY pyproject.toml uv.lock README.md ./
# The docs build generates PNG example figures, which need Pillow (the png extra).
RUN --mount=type=cache,target=/root/.cache/uv,id=pystrich-uv \
    uv sync --frozen --no-install-project --no-default-groups --group docs --extra png

COPY . .
RUN --mount=type=cache,target=/root/.cache/uv,id=pystrich-uv \
    uv sync --frozen --no-default-groups --group docs --extra png

RUN uv run --frozen --no-sync sphinx-build -W --keep-going -b doctest -d docs/_build/.doctrees docs docs/_build/doctest
RUN uv run --frozen --no-sync sphinx-build -W --keep-going -b text -d docs/_build/.doctrees docs docs/_build/text
RUN uv run --frozen --no-sync sphinx-build -W --keep-going -b html -d docs/_build/.doctrees docs docs/_build/html
RUN uv run --frozen --no-sync sphinx-build -W --keep-going -b text -D language=de_DE -d docs/_build/.doctrees-de_DE docs docs/_build/text/de
RUN uv run --frozen --no-sync sphinx-build -W --keep-going -b html -D language=de_DE -D html_baseurl=https://www.method-b.uk/pyStrich/docs/de/ -d docs/_build/.doctrees-de_DE docs docs/_build/html/de

FROM scratch AS export
COPY --from=build /src/docs/_build/html /html
COPY --from=build /src/docs/_build/text /text