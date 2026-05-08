#!/usr/bin/env bash
# Run the test suite against every supported Python version in podman.
#
# Order is fail-fast and newest-first. The newest Python image is built up
# front so the static checks (ruff, ruff format, mypy) run against it before
# any pytest matrix work, then pytest runs newest-first across the matrix.
# The first failing step aborts the whole script.
set -uo pipefail

VERSIONS=(3.14 3.13 3.12 3.11 3.10)
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
DOCKERFILE="$HERE/test-python-versions.Dockerfile"
STATIC_TAG="pystrich-test:${VERSIONS[0]}"

verbose=0
latest_only=0
for arg in "$@"; do
    case "$arg" in
        -v|--verbose) verbose=1 ;;
        --latest) latest_only=1 ;;
        -h|--help)
            echo "Usage: $0 [--verbose] [--latest]"
            echo "  --latest   only build/test the newest Python (${VERSIONS[0]})"
            exit 0
            ;;
        *)
            echo "Unknown argument: $arg" >&2
            exit 2
            ;;
    esac
done

cleanup() {
    # Drop pystrich-test tags not in the current VERSIONS set, then prune any
    # dangling pystrich-test images (identified by the OCI title label).
    local keep=" ${VERSIONS[*]} "
    while read -r tag id; do
        [[ "$keep" == *" $tag "* ]] || podman rmi -f "$id" >/dev/null 2>&1 || true
    done < <(podman images --filter "reference=pystrich-test" --format '{{.Tag}} {{.ID}}')
    podman image prune -f --filter "label=org.opencontainers.image.title=pystrich-test" >/dev/null
}
trap cleanup EXIT

run_step() {
    local label="$1"
    shift
    local start end elapsed status
    start=$EPOCHREALTIME
    if (( verbose )); then
        echo "=== ${label} ==="
        "$@"
        status=$?
        end=$EPOCHREALTIME
        elapsed=$(awk "BEGIN { printf \"%.1fs\", $end - $start }")
        if (( status == 0 )); then
            echo "${label}: PASS in ${elapsed}"
        else
            echo "${label}: FAIL in ${elapsed}"
            exit 1
        fi
    else
        local output
        output=$("$@" 2>&1)
        status=$?
        end=$EPOCHREALTIME
        elapsed=$(awk "BEGIN { printf \"%.1fs\", $end - $start }")
        if (( status == 0 )); then
            echo "${label}: PASS in ${elapsed}"
        else
            echo "${label}: FAIL in ${elapsed}"
            echo "$output"
            exit 1
        fi
    fi
}

build_version() {
    local v="$1"
    podman build \
        --build-arg "PYTHON_VERSION=${v}" \
        -f "$DOCKERFILE" \
        -t "pystrich-test:${v}" \
        "$ROOT"
}

run_pytest() {
    local v="$1"
    podman run --rm "pystrich-test:${v}"
}

run_ruff() {
    podman run --rm "$STATIC_TAG" uv run --frozen ruff check
}

run_ruff_format() {
    podman run --rm "$STATIC_TAG" uv run --frozen ruff format --check
}

run_mypy() {
    podman run --rm "$STATIC_TAG" uv run --frozen mypy
}

# Build the newest Python image first; static checks share it.
run_step "Build Python ${VERSIONS[0]}" build_version "${VERSIONS[0]}"

# Static checks: cheap, share one image, fail before pytest spends ~5min.
run_step "ruff" run_ruff
run_step "ruff format" run_ruff_format
run_step "mypy" run_mypy

# Pytest, newest-first. The first version's image is already built.
run_step "Python ${VERSIONS[0]}" run_pytest "${VERSIONS[0]}"
if (( ! latest_only )); then
    for v in "${VERSIONS[@]:1}"; do
        run_step "Build Python ${v}" build_version "${v}"
        run_step "Python ${v}" run_pytest "${v}"
    done
fi
