#!/usr/bin/env bash
# Build the docs into docs/_build/{html,text} via podman.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
DOCKERFILE="$HERE/build-docs.Dockerfile"
OUTPUT="$ROOT/docs/_build"

rm -rf "$OUTPUT/html" "$OUTPUT/text"
podman build -f "$DOCKERFILE" --target export -o "$OUTPUT" "$ROOT"
podman image prune -f --filter "label=org.opencontainers.image.title=pystrich-docs" >/dev/null
