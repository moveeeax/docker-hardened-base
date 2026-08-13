# syntax=docker/dockerfile:1.7
# hardened-python — minimal, non-root base for pure-Python services.
#
# Runtime layer is gcr.io/distroless/python3: a CPython interpreter with no
# shell and no package manager. Pinned by digest; the :nonroot variant runs as
# uid 65532. Bring your dependencies as a wheel layer or a copied virtualenv;
# this example ships a stdlib-only app so the base stays dependency-free.
FROM gcr.io/distroless/python3-debian12@sha256:7d1042ce588ab97019fe95c24ffca7bc5a82ccdac572511d5e09bda4435c89c5
LABEL org.opencontainers.image.title="hardened-python" \
      org.opencontainers.image.description="Minimal distroless base for Python services" \
      org.opencontainers.image.source="https://github.com/moveeeax/docker-hardened-base" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.base.name="gcr.io/distroless/python3-debian12:nonroot"
WORKDIR /app
COPY examples/python/app.py /app/app.py
# uid:gid 65532 (nonroot), enforced numerically for runAsNonRoot policies.
USER 65532:65532
EXPOSE 8080
ENTRYPOINT ["python3", "/app/app.py"]
