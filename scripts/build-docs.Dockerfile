FROM python:3.13-slim AS build

RUN pip install --no-cache-dir poetry

WORKDIR /src

COPY pyproject.toml poetry.lock README.md ./
RUN poetry install --with docs --no-root

COPY . .
RUN poetry install --with docs

RUN poetry run sphinx-build -W --keep-going -b doctest docs docs/_build/doctest
RUN poetry run sphinx-build -W --keep-going -b text docs docs/_build/text
RUN poetry run sphinx-build -W --keep-going -b html docs docs/_build/html

FROM scratch AS export
COPY --from=build /src/docs/_build/html /html
COPY --from=build /src/docs/_build/text /text
