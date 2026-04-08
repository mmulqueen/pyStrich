#!/usr/bin/env bash
# Run the test suite against every supported Python version in podman.
set -uo pipefail

VERSIONS=(3.10 3.11 3.12 3.13 3.14)
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
DOCKERFILE="$HERE/test-python-versions.Dockerfile"

verbose=0
for arg in "$@"; do
    case "$arg" in
        -v|--verbose) verbose=1 ;;
        -h|--help)
            echo "Usage: $0 [--verbose]"
            exit 0
            ;;
        *)
            echo "Unknown argument: $arg" >&2
            exit 2
            ;;
    esac
done

run_version() {
    local v="$1"
    local tag="pystrich-test:${v}"
    podman build \
        --build-arg "PYTHON_VERSION=${v}" \
        -f "$DOCKERFILE" \
        -t "$tag" \
        "$ROOT" \
    && podman run --rm "$tag"
}

status=0
for v in "${VERSIONS[@]}"; do
    if (( verbose )); then
        echo "=== Python ${v} ==="
        if run_version "$v"; then
            echo "Python ${v}: PASS"
        else
            echo "Python ${v}: FAIL"
            status=1
        fi
    else
        if output=$(run_version "$v" 2>&1); then
            echo "Python ${v}: PASS"
        else
            echo "Python ${v}: FAIL"
            echo "$output"
            status=1
        fi
    fi
done

exit $status
