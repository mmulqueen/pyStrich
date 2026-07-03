#!/usr/bin/env bash
# Build the docs into docs/_build/{html,text} via podman.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
DOCKERFILE="$HERE/build-docs.Dockerfile"
OUTPUT="$ROOT/docs/_build"

rm -rf "$OUTPUT/html" "$OUTPUT/text"
# Tag the heavy 'build' stage so its layers survive as cache; the export build
# then reuses them. The prune drops the previous (now-dangling) cache generation
# but keeps this freshly-tagged latest one.
podman build -f "$DOCKERFILE" --target build -t pystrich-docs:cache "$ROOT"
podman build -f "$DOCKERFILE" --target export -o "$OUTPUT" "$ROOT"

# Drop any pystrich-docs tags other than the cache tag, then prune dangling
# pystrich-docs images (identified by the OCI title label).
while read -r tag id; do
    [[ "$tag" == "cache" ]] || podman rmi -f "$id" >/dev/null 2>&1 || true
done < <(podman images --filter "reference=pystrich-docs" --format '{{.Tag}} {{.ID}}')
podman image prune -f --filter "label=org.opencontainers.image.title=pystrich-docs" >/dev/null
