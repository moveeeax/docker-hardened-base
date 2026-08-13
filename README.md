# docker-hardened-base

[![CI](https://github.com/moveeeax/docker-hardened-base/actions/workflows/ci.yml/badge.svg)](https://github.com/moveeeax/docker-hardened-base/actions/workflows/ci.yml)
![Dockerfile](https://img.shields.io/badge/base-Dockerfile-2496ED?logo=docker&logoColor=white)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> Tiny, CVE-lean base images your services can actually trust.

Minimal, distroless-style base images for **Go** and **Python** services. Each
image ships the least it can: no shell, no package manager, a digest-pinned
upstream, non-root by default, and a policy check that fails the build if any of
those promises slip.

| Image | Base | Runtime size | Runs as |
|-------|------|--------------|---------|
| `hardened-go` | `gcr.io/distroless/static-debian12` (pinned) | ~12 MB | uid 65532 |
| `hardened-python` | `gcr.io/distroless/python3-debian12` (pinned) | ~90 MB | uid 65532 |

## Why

"Use distroless" is easy advice and easy to quietly undo — someone adds a
`RUN apt-get install`, flips `USER` back to root to debug, or pins to `:latest`
and the image is no longer hardened. This repo turns the hardening rules into a
**linter** (`scripts/policy.py`) that CI blocks on, so the images can't rot into
a fat, root-running base without a red check.

The policy enforced on the final runtime stage:

| Code | Rule |
|------|------|
| DHB001 | final base is pinned by `@sha256:` digest |
| DHB002 | no mutable / `:latest` runtime tag |
| DHB003 | no `RUN` in the final stage (implies a shell) |
| DHB004 | no package manager in the final stage |
| DHB005 | drops root (`USER` is non-root) |
| DHB006 | no privileged (`<1024`) `EXPOSE` — non-root can't bind it |
| DHB007 | carries OCI `source` + `licenses` labels |

## Usage

Build a service on `hardened-go` — a fully static binary on a shell-less base:

```dockerfile
FROM golang:1.22-alpine AS build
WORKDIR /src
ENV CGO_ENABLED=0
COPY . .
RUN go build -ldflags="-s -w" -o /out/app .

FROM ghcr.io/moveeeax/hardened-go:1.22
COPY --from=build /out/app /app
USER 65532:65532
ENTRYPOINT ["/app"]
```

Or run the bundled examples locally:

```console
$ ./scripts/build.sh            # builds hardened-go:dev and hardened-python:dev
$ docker run --rm -p 8080:8080 ghcr.io/moveeeax/hardened-go:dev &
$ curl -s localhost:8080/whoami
uid=65532 gid=65532
```

Multi-arch build & push:

```console
$ PLATFORMS=linux/amd64,linux/arm64 PUSH=1 TAG=1.22 ./scripts/build.sh go
```

## How it works

- `images/go/Dockerfile` builds a static, stripped Go binary in a `golang`
  builder stage and copies it onto `distroless/static` — nothing else lands in
  the runtime layer.
- `images/python/Dockerfile` layers a stdlib app onto `distroless/python3`; the
  interpreter is the entrypoint, and there is still no shell.
- `scripts/policy.py` parses each Dockerfile into build stages and asserts the
  rules above on the *final* stage. It has no dependencies and exits non-zero
  with one line per violation, so it slots into any CI step.
- CI (`.github/workflows/ci.yml`) runs the linter and unit tests, builds both
  images, scans them with **Trivy** (blocking on HIGH/CRITICAL), emits an
  **SPDX SBOM** per image with **Syft**, and runs the bats smoke tests.

## Testing

```console
$ python3 -m unittest discover -s test -p '*_test.py'   # policy unit tests, no daemon
$ bats test/smoke.bats                                  # builds + runs the images
```

## License

MIT — see [LICENSE](LICENSE).
