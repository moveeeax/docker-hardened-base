#!/usr/bin/env bats
# Integration smoke tests: build each hardened image, then assert the runtime
# invariants that the policy linter can only promise on paper — the process
# really runs as non-root and there is genuinely no shell in the image.
#
# Requires a working Docker daemon. Skips gracefully when Docker is absent so
# the pure-unit suite still gates CI on hosts without a daemon.

setup_file() {
  if ! docker info >/dev/null 2>&1; then
    export DHB_NO_DOCKER=1
    return
  fi
  cd "${BATS_TEST_DIRNAME}/.."
  docker build -q -f images/go/Dockerfile -t dhb-go:test . >/dev/null
  docker build -q -f images/python/Dockerfile -t dhb-python:test . >/dev/null
}

teardown_file() {
  docker rmi -f dhb-go:test dhb-python:test >/dev/null 2>&1 || true
}

_skip_if_no_docker() {
  if [ -n "${DHB_NO_DOCKER:-}" ]; then skip "docker daemon unavailable"; fi
  return 0
}

@test "hardened-go runs as non-root uid 65532" {
  _skip_if_no_docker
  # Start the server on an ephemeral host port and read uid from /whoami.
  run bash -c 'cid=$(docker run -d -p 0:8080 dhb-go:test); sleep 1; \
    port=$(docker port "$cid" 8080 | head -1 | sed "s/.*://"); \
    curl -sf "http://127.0.0.1:$port/whoami"; docker rm -f "$cid" >/dev/null'
  [ "$status" -eq 0 ]
  [[ "$output" == *"uid=65532"* ]]
}

@test "hardened-go has no shell in the runtime layer" {
  _skip_if_no_docker
  run docker run --rm --entrypoint /bin/sh dhb-go:test -c "echo pwned"
  [ "$status" -ne 0 ]
  [[ "$output" != *"pwned"* ]]
}

@test "hardened-python runs as non-root uid 65532" {
  _skip_if_no_docker
  run bash -c 'cid=$(docker run -d -p 0:8080 dhb-python:test); sleep 1; \
    port=$(docker port "$cid" 8080 | head -1 | sed "s/.*://"); \
    curl -sf "http://127.0.0.1:$port/whoami"; docker rm -f "$cid" >/dev/null'
  [ "$status" -eq 0 ]
  [[ "$output" == *"uid=65532"* ]]
}

@test "hardened-python has no shell in the runtime layer" {
  _skip_if_no_docker
  run docker run --rm --entrypoint /bin/sh dhb-python:test -c "echo pwned"
  [ "$status" -ne 0 ]
  [[ "$output" != *"pwned"* ]]
}
