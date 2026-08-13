#!/usr/bin/env bash
# Build the hardened base images. Multi-arch by default via buildx; falls back
# to a single-arch `docker build` when no builder or --load is requested.
#
#   scripts/build.sh                       # build both, load into the local daemon
#   PLATFORMS=linux/amd64,linux/arm64 \
#     PUSH=1 REGISTRY=ghcr.io/moveeeax \
#     TAG=1.22 scripts/build.sh go         # multi-arch build + push of hardened-go
set -euo pipefail

cd "$(dirname "$0")/.."

REGISTRY="${REGISTRY:-ghcr.io/moveeeax}"
TAG="${TAG:-dev}"
PLATFORMS="${PLATFORMS:-}"
PUSH="${PUSH:-0}"
TARGETS=("${@:-go python}")
# shellcheck disable=SC2206
TARGETS=(${TARGETS[@]})

build_one() {
  local name="$1"
  local image="${REGISTRY}/hardened-${name}:${TAG}"
  local dockerfile="images/${name}/Dockerfile"
  echo ">> building ${image} from ${dockerfile}"

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
