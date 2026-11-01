#!/usr/bin/env bash
# Build the hardened base images. Multi-arch by default via buildx; falls back
# to a single-arch `docker build` when no builder or --load is requested.
#
#   scripts/build.sh                       # build both as hardened-{go,python}:dev
#   PLATFORMS=linux/amd64,linux/arm64 \
#     PUSH=1 REGISTRY=ghcr.io/<you> \
#     TAG=1.27 scripts/build.sh go         # multi-arch build + push to your registry
#
# No registry is assumed: without REGISTRY the images are tagged locally only.
set -euo pipefail

cd "$(dirname "$0")/.."

REGISTRY="${REGISTRY:-}"
TAG="${TAG:-dev}"
PLATFORMS="${PLATFORMS:-}"
PUSH="${PUSH:-0}"
TARGETS=("${@:-go python}")
# shellcheck disable=SC2206
TARGETS=(${TARGETS[@]})

build_one() {
  local name="$1"
  local image="${REGISTRY:+${REGISTRY}/}hardened-${name}:${TAG}"
  local dockerfile="images/${name}/Dockerfile"
  echo ">> building ${image} from ${dockerfile}"
  if [[ "${PUSH}" == "1" && -z "${REGISTRY}" ]]; then
    echo "PUSH=1 needs REGISTRY (e.g. REGISTRY=ghcr.io/<you>)" >&2
    exit 1
  fi

  local args=(--file "${dockerfile}" --tag "${image}")
  if [[ -n "${PLATFORMS}" ]]; then
    args+=(--platform "${PLATFORMS}")
    [[ "${PUSH}" == "1" ]] && args+=(--push) || args+=(--load)
    docker buildx build "${args[@]}" .
  else
    [[ "${PUSH}" == "1" ]] && args+=(--push)
    docker build "${args[@]}" .
  fi
}

for t in "${TARGETS[@]}"; do
  build_one "${t}"
done
