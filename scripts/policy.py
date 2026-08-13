#!/usr/bin/env python3
"""Hardening-policy linter for base-image Dockerfiles.

A base image is only "hardened" if the *final* runtime stage keeps its
promises: no root, no shell/package-manager surface, a digest-pinned base and
enough OCI metadata to trace provenance. This module parses a Dockerfile into
build stages and checks those invariants on the final stage. It has no third-
party dependencies so it runs anywhere Python 3.8+ does, and it is the unit that
CI blocks on before a single layer is built.

Exit code is the number of violations (0 == clean), so it drops straight into a
`bash -e` CI step.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Stage:
    base: str
    name: Optional[str]
    start_line: int
    instructions: List[tuple] = field(default_factory=list)  # (op, args, lineno)


@dataclass
class Finding:
    code: str
    message: str
    line: int

    def __str__(self) -> str:
        return f"{self.line:>4}: [{self.code}] {self.message}"


_PKG_MANAGERS = ("apt-get", "apt ", "apk ", "yum ", "dnf ", "microdnf", "zypper")


def _logical_lines(text: str):
    """Yield (lineno, content) joining backslash continuations, dropping
    comments and blank lines. lineno is the 1-based line the statement starts."""
    buf = ""
    start = 0
    for i, raw in enumerate(text.splitlines(), start=1):
        line = raw.rstrip()
        stripped = line.strip()
        if not buf and (not stripped or stripped.startswith("#")):
            continue
        if not buf:
            start = i
        if line.endswith("\\"):
            buf += line[:-1] + " "
            continue
        buf += line
        yield start, buf.strip()
        buf = ""
    if buf.strip():
        yield start, buf.strip()


def parse(text: str) -> List[Stage]:
    stages: List[Stage] = []
    for lineno, line in _logical_lines(text):
        op, _, rest = line.partition(" ")
        op = op.upper()
        if op == "FROM":
            tokens = rest.split()
            base = tokens[0] if tokens else ""
            name = None
            if len(tokens) >= 3 and tokens[1].upper() == "AS":
                name = tokens[2]
            stages.append(Stage(base=base, name=name, start_line=lineno))
        elif stages:
            stages[-1].instructions.append((op, rest.strip(), lineno))
    return stages


def _base_is_build_stage(base: str, stages: List[Stage]) -> bool:
    return any(s.name and s.name == base for s in stages)


def lint(text: str) -> List[Finding]:
    stages = parse(text)
    findings: List[Finding] = []
    if not stages:
        return [Finding("DHB000", "no FROM instruction found", 1)]

    final = stages[-1]

    # DHB001 — final base pinned by digest (reproducible supply chain).
    if not _base_is_build_stage(final.base, stages) and "@sha256:" not in final.base:
        findings.append(
            Finding("DHB001", f"final base '{final.base}' is not pinned by @sha256 digest",
                    final.start_line)
        )
    # DHB002 — never ship a floating :latest / untagged runtime base. A digest
    # pin (@sha256:) is immutable, so it needs no tag.
    if not _base_is_build_stage(final.base, stages) and "@sha256:" not in final.base:
        ref = final.base
        if ":" not in ref.split("/")[-1] or ref.endswith(":latest"):
            findings.append(
                Finding("DHB002", f"final base '{final.base}' uses a mutable/latest tag",
                        final.start_line)
            )

    user = None
    user_line = final.start_line
    exposes: List[tuple] = []
    labels: List[str] = []
    for op, args, lineno in final.instructions:
        if op == "USER":
            user, user_line = args, lineno
        elif op == "EXPOSE":
            exposes.append((args, lineno))
        elif op == "LABEL":
            labels.append(args)
        elif op == "RUN":
            # DHB003 — a distroless runtime has no shell; a RUN in the final
            # stage means the base still carries one (attack surface).
            findings.append(
                Finding("DHB003", "RUN in final stage implies a shell in the runtime layer", lineno)
            )
            low = args.lower()
            if any(p in low for p in _PKG_MANAGERS):
                findings.append(
                    Finding("DHB004", "package manager invoked in final stage", lineno)
                )

    # DHB005 — must drop root.
    if user is None:
        findings.append(Finding("DHB005", "final stage never sets USER (runs as root)", final.start_line))
    elif user.split(":")[0] in ("root", "0"):
        findings.append(Finding("DHB005", f"final stage runs as root (USER {user})", user_line))

    # DHB006 — a non-root process cannot bind privileged ports (<1024).
    for args, lineno in exposes:
        for tok in args.split():
            portspec = tok.split("/")[0]
            if portspec.isdigit() and int(portspec) < 1024:
                findings.append(
                    Finding("DHB006", f"EXPOSE {tok} is a privileged port unbindable by non-root", lineno)
                )

    # DHB007 — provenance metadata.
    label_blob = " ".join(labels)
    for key in ("org.opencontainers.image.source", "org.opencontainers.image.licenses"):
        if key not in label_blob:
            findings.append(Finding("DHB007", f"missing OCI label {key}", final.start_line))

    return findings


def lint_file(path: str) -> List[Finding]:
    with open(path, "r", encoding="utf-8") as fh:
        return lint(fh.read())


def main(argv: List[str]) -> int:
    paths = argv[1:]
    if not paths:
        print("usage: policy.py <Dockerfile> [Dockerfile ...]", file=sys.stderr)
        return 2
    total = 0
    for path in paths:
        findings = lint_file(path)
        if findings:
            print(f"✗ {path}")
            for f in findings:
                print(f"  {f}")
        else:
            print(f"✓ {path}")
        total += len(findings)
    print(f"\n{total} violation(s)")
    return total


if __name__ == "__main__":
    sys.exit(main(sys.argv))
