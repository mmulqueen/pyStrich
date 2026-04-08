ARG PYTHON_VERSION=3.13
FROM python:${PYTHON_VERSION}-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends dmtx-utils \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir poetry

WORKDIR /src

# Install dependencies first so the layer can be cached across source edits.
COPY pyproject.toml poetry.lock ./
COPY README.md ./
RUN poetry install --with dev --no-root

COPY . .
RUN poetry install --with dev

CMD ["poetry", "run", "pytest"]
