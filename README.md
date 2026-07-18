# docker-hardened-base

> Tiny, CVE-lean base images your services can actually trust.

**Status:** 🚧 In development

## Overview

Minimal, hardened base images (distroless-style) for Go and Python services.

## Features

- Multi-arch (amd64/arm64) minimal images
- Non-root user, read-only friendly, no shell in runtime
- SBOM + provenance attestations
- Trivy-scanned in CI with zero-high policy
- Go and Python runtime variants

## Stack

Docker Buildx + Trivy + Syft; GitHub Actions build/push.

## Usage

```yaml
FROM ghcr.io/cybercapybara/hardened-go:1.22 AS run
```

## License

MIT
