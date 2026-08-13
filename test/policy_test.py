#!/usr/bin/env python3
"""Unit tests for the hardening-policy linter.

Runs with the stdlib only: `python3 -m unittest discover -s test`.
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import policy  # noqa: E402


def codes(text):
    return sorted({f.code for f in policy.lint(text)})


class ShippedImagesTest(unittest.TestCase):
    """The Dockerfiles we actually publish must be clean."""

    def test_go_image_is_clean(self):
        findings = policy.lint_file(os.path.join(ROOT, "images/go/Dockerfile"))
        self.assertEqual([], findings, msg="\n".join(str(f) for f in findings))

    def test_python_image_is_clean(self):
        findings = policy.lint_file(os.path.join(ROOT, "images/python/Dockerfile"))
        self.assertEqual([], findings, msg="\n".join(str(f) for f in findings))


class RootUserTest(unittest.TestCase):
    def test_no_user_flags_root(self):
        df = (
            "FROM gcr.io/distroless/static-debian12@sha256:" + "a" * 64 + "\n"
            'LABEL org.opencontainers.image.source="x" org.opencontainers.image.licenses="MIT"\n'
            "COPY app /app\n"
        )
        self.assertIn("DHB005", codes(df))

    def test_explicit_root_flags(self):
        df = (
            "FROM gcr.io/distroless/static-debian12@sha256:" + "a" * 64 + "\n"
            'LABEL org.opencontainers.image.source="x" org.opencontainers.image.licenses="MIT"\n'
            "USER root\n"
        )
        self.assertIn("DHB005", codes(df))

    def test_nonroot_numeric_is_ok(self):
        df = (
            "FROM gcr.io/distroless/static-debian12@sha256:" + "a" * 64 + "\n"
            'LABEL org.opencontainers.image.source="x" org.opencontainers.image.licenses="MIT"\n'
            "USER 65532:65532\n"
        )
        self.assertNotIn("DHB005", codes(df))


class SupplyChainTest(unittest.TestCase):
    def test_unpinned_base_flagged(self):
        df = (
            "FROM alpine:3.20\n"
            'LABEL org.opencontainers.image.source="x" org.opencontainers.image.licenses="MIT"\n'
            "USER 65532\n"
        )
        c = codes(df)
        self.assertIn("DHB001", c)

    def test_latest_tag_flagged(self):
        df = (
            "FROM alpine:latest\n"
            'LABEL org.opencontainers.image.source="x" org.opencontainers.image.licenses="MIT"\n'
            "USER 65532\n"
        )
        self.assertIn("DHB002", codes(df))

    def test_build_stage_reference_is_exempt(self):
        # A final FROM that points at a named build stage is not an external base.
        df = (
            "FROM golang:1.22-alpine AS build\n"
            "RUN go build -o /app .\n"
            "FROM build\n"
            'LABEL org.opencontainers.image.source="x" org.opencontainers.image.licenses="MIT"\n'
            "USER 65532\n"
        )
        c = codes(df)
        self.assertNotIn("DHB001", c)
        self.assertNotIn("DHB002", c)


class ShellSurfaceTest(unittest.TestCase):
    def test_run_in_final_stage_flagged(self):
        df = (
            "FROM debian:12@sha256:" + "b" * 64 + "\n"
            'LABEL org.opencontainers.image.source="x" org.opencontainers.image.licenses="MIT"\n'
            "RUN apt-get update && apt-get install -y curl\n"
            "USER 65532\n"
        )
        c = codes(df)
        self.assertIn("DHB003", c)  # shell present
        self.assertIn("DHB004", c)  # package manager

    def test_multiline_run_counted_once(self):
        df = (
            "FROM debian:12@sha256:" + "b" * 64 + "\n"
            'LABEL org.opencontainers.image.source="x" org.opencontainers.image.licenses="MIT"\n'
            "RUN apt-get update \\\n"
            "    && apt-get install -y curl\n"
            "USER 65532\n"
        )
        findings = policy.lint(df)
        self.assertEqual(1, sum(1 for f in findings if f.code == "DHB003"))


class PrivilegedPortTest(unittest.TestCase):
    def test_low_port_flagged(self):
        df = (
            "FROM gcr.io/distroless/static-debian12@sha256:" + "a" * 64 + "\n"
            'LABEL org.opencontainers.image.source="x" org.opencontainers.image.licenses="MIT"\n'
            "USER 65532\n"
            "EXPOSE 80\n"
        )
        self.assertIn("DHB006", codes(df))

    def test_high_port_ok(self):
        df = (
            "FROM gcr.io/distroless/static-debian12@sha256:" + "a" * 64 + "\n"
            'LABEL org.opencontainers.image.source="x" org.opencontainers.image.licenses="MIT"\n'
            "USER 65532\n"
            "EXPOSE 8080/tcp\n"
        )
        self.assertNotIn("DHB006", codes(df))


class MetadataTest(unittest.TestCase):
    def test_missing_labels_flagged(self):
        df = (
            "FROM gcr.io/distroless/static-debian12@sha256:" + "a" * 64 + "\n"
            "USER 65532\n"
        )
        self.assertIn("DHB007", codes(df))


if __name__ == "__main__":
    unittest.main()
