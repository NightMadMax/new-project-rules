#!/usr/bin/env python3
"""What must never be in the repository: secrets, machine paths, real base names.

The readiness criterion asks for a scanner rather than a review, and the reason
is that a review sees what it looks at. A committed token stays valid after the
commit is reverted, and a machine path in a shared template is a file that only
works for the person who wrote it.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCANNED = ("templates", "scripts", "docs", "config", ".agents", ".claude", ".github")
TEXT_SUFFIXES = {
    ".md", ".py", ".sh", ".ps1", ".json", ".tsv", ".yaml", ".yml", ".toml", ".txt",
    ".env", ".template", ".launch", ".cfg", ".ini",
}
SKIP_PARTS = {"__pycache__", ".git", "node_modules"}
SKIP_NAMES = {".DS_Store", "Thumbs.db"}
# A test of this scanner has to contain what the scanner forbids. The exemption
# is a word on the line, so it is explicit, greppable, and impossible to grant
# by accident to a file nobody read.
MARKER = "noscan"

# Each pattern is a thing that cannot be there, not a thing that looks odd.
FINDINGS = (
    ("secret.assigned", re.compile(
        # No leading word boundary: the usual name is DEFAULT_PASSWORD, and an
        # underscore is a word character, so \b would look straight past it.
        r"(?i)[a-z0-9_]*(password|passwd|secret|token|api[_-]?key|access[_-]?key)[a-z0-9_]*"
        # The value has to look like a secret, not like code: a quoted string
        # or a bare word. "tokens = [token[1:-1]" is an assignment too.
        # The value has to look like a secret, not like code: a quoted string,
        # or a bare word with no dots — "tokens = [token[1:-1]" and
        # "token_option = arguments.token_option" are assignments too.
        r"\s*[:=]\s*(?:[\"'][^\"'\n]{6,}[\"']|[A-Za-z0-9_/+-]{6,}\s*$)"),
     "a credential with a value"),
    ("secret.private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "a private key"),
    ("secret.connection", re.compile(
        r"(?i)(srvr\s*=\s*[\"']?[^\s\"';]+[\"']?\s*;\s*ref\s*=|(postgres|mysql|mongodb|mssql)://[^\s\"']*:[^\s\"'@]+@)"),
     "a connection string with a host or a password"),
    ("path.home", re.compile(r"(/Users/|/home/|[A-Za-z]:\\\\Users\\\\)(?!<)[A-Za-z0-9._-]+"),
     "an absolute path to somebody's home directory"),
)
# Placeholders are the point of a template, and a rule needs an example of what
# it forbids. Both are text about the pattern, not an instance of it.
ALLOWED = re.compile(
    r"(<[A-Z_]+>|\bexample\b|\bEXAMPLE\b|\bpath/to\b|/path/|\bуказыва|\bплейсхолдер|"
    r"\bпример\b|\bнапример\b|placeholder|dummy|xxxx|\.\.\.)")

failures: list[str] = []


def scanned_files() -> list[Path]:
    files = []
    for name in SCANNED:
        base = ROOT / name
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.is_symlink():
                continue
            if SKIP_PARTS & set(path.parts) or path.name in SKIP_NAMES:
                continue
            if path.suffix.lower() in TEXT_SUFFIXES or not path.suffix:
                files.append(path)
    return files


def scan(text: str) -> list[tuple[str, str, int, str]]:
    """(code, description, line number, the line) for every real finding."""
    found = []
    for number, line in enumerate(text.splitlines(), start=1):
        if MARKER in line or ALLOWED.search(line):
            continue
        for code, pattern, description in FINDINGS:
            if pattern.search(line):
                found.append((code, description, number, line.strip()[:120]))
    return found


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    for path in scanned_files():
        try:
            text = path.read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            failures.append(f"{path.relative_to(ROOT).as_posix()}: not UTF-8")
            continue
        for code, description, number, line in scan(text):
            failures.append(f"{path.relative_to(ROOT).as_posix()}:{number} [{code}] {description}: {line}")

    # The scanner has to be able to see what it is looking for; otherwise a
    # broken pattern reads as a clean repository.
    samples = (
        ("PASSWORD=hunter2xyz", "secret.assigned"),  # noscan
        ("DEFAULT_PASSWORD=hunter2xyz", "secret.assigned"),  # noscan
        ("ONEC_API_TOKEN = 'abcdef123456'", "secret.assigned"),  # noscan
        ('api_key: "sk-ABCDEF012345"', "secret.assigned"),  # noscan
        ("-----BEGIN RSA PRIVATE KEY-----", "secret.private-key"),  # noscan
        ('Srvr="10.0.0.5";Ref="erp-prod";', "secret.connection"),  # noscan
        ("postgres://user:hunter2@db.internal:5432/erp", "secret.connection"),  # noscan
        ("/Users/ivan/work/erp", "path.home"),  # noscan
        ("C:\\\\Users\\\\ivan\\\\erp", "path.home"),  # noscan
    )
    for line, expected in samples:
        codes = {code for code, _, _, _ in scan(line)}
        if expected not in codes:
            failures.append(f"the scanner misses '{line}': expected {expected}, got {codes or 'nothing'}")

    for line in ("PASSWORD=<PASSWORD>", "DEFAULT_PASSWORD=", "путь вида /Users/<user>/project — пример",
                 "tokens = [token[1:-1] for token in split(command)]",
                 "token_option = arguments.token_option"):
        if scan(line):
            failures.append(f"the scanner must not fire on '{line}'")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        print(f"{len(failures)} secret scan finding(s).", file=sys.stderr)
        raise SystemExit(1)

    print("No secrets, machine paths or real base names found.")
