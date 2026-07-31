#!/usr/bin/env python3
"""What must never be in the repository: secrets, machine paths, real base names.

The readiness criterion asks for a scanner rather than a review, and the reason
is that a review sees what it looks at. A committed token stays valid after the
commit is reverted, and a machine path in a shared template is a file that only
works for the person who wrote it.
"""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parent.parent
# The whole working tree, not a list of directories somebody remembered to add.
# Git history is out of scope on purpose: a leak there needs a rewrite, not a
# fix, and that is a different job from keeping the tree clean.
SKIP_DIRECTORIES = {".git", "__pycache__", "node_modules", ".obsidian", ".trash"}
TEXT_SUFFIXES = {
    ".md", ".py", ".sh", ".ps1", ".json", ".tsv", ".yaml", ".yml", ".toml", ".txt",
    ".env", ".template", ".launch", ".cfg", ".ini",
    # A created project holds the configuration sources, and a connection string
    # or a base name would live exactly there.
    ".xml", ".bsl", ".os", ".mdo", ".html",
}
SKIP_NAMES = {".DS_Store", "Thumbs.db"}
# A test of this scanner has to contain what the scanner forbids. The exemption
# is a word on the line, so it is explicit, greppable, and impossible to grant
# by accident to a file nobody read.
MARKER = re.compile(r"(?:#|<!--|//|;)\s*noscan\b")

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
        r"\s*[:=]\s*(?:[\"'][^\"'\n]{6,}[\"']|[A-Za-z0-9_/+-]{6,}(?=\s*(?:#|<!--|//|;|$)))"),
     "a credential with a value"),
    ("secret.private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "a private key"),
    # A secret does not need a name beside it to be a secret: these shapes are
    # issued tokens, and finding one is enough on its own.
    ("secret.token", re.compile(
        r"(gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|xox[baprs]-[A-Za-z0-9-]{10,}"
        r"|AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9]{20,}|eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.)"),
     "a token in a form somebody issues"),
    ("secret.connection", re.compile(
        r"(?i)(srvr\s*=\s*[\"']?[^\s\"';]+[\"']?\s*;\s*ref\s*=|(postgres|mysql|mongodb|mssql)://[^\s\"']*:[^\s\"'@]+@)"),
     "a connection string with a host or a password"),
    # One backslash or two: a path written in Markdown, an .ini or a .ps1 has a
    # single one, and requiring the escaped form meant seeing only source code —
    # on a capability whose target platform is Windows.
    ("path.home", re.compile(r"(?i)(/Users/|/home/|[a-z]:[\\/]{1,2}users[\\/]{1,2})(?!<)[a-z0-9._-]+"),
     "an absolute path to somebody's home directory"),
)
# Placeholders are the point of a template. This is matched against the piece
# that fired, never against the whole line: a whitelist that reads the line
# would let any comment — "# пример", "# example" — switch every check off.
ALLOWED = re.compile(
    r"(<[A-Za-z_]+>|\{[a-z_]+\}|path/to|/path/|\$\{[A-Za-z_]+\}|%[A-Za-z_]+%"
    # The build machine's own directories: documenting a pipeline means naming
    # them, and they belong to nobody.
    r"|/home/runner|/Users/runner|/home/vsts)")

failures: list[str] = []


def scanned_files(root: Path) -> list[Path]:
    files = []
    for path in root.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        if SKIP_DIRECTORIES & set(path.parts) or path.name in SKIP_NAMES:
            continue
        if path.suffix.lower() in TEXT_SUFFIXES or not path.suffix:
            files.append(path)
    return files


def scan(text: str) -> list[tuple[str, str, int, str]]:
    """(code, description, line number, the line) for every real finding."""
    found = []
    for number, line in enumerate(text.splitlines(), start=1):
        if MARKER.search(line):
            continue
        for code, pattern, description in FINDINGS:
            match = pattern.search(line)
            # The exemption applies to what matched, not to the line around it.
            if match and not ALLOWED.search(match.group(0)):
                found.append((code, description, number, line.strip()[:120]))
    return found


REGISTRY = "config/1c-projects.tsv"
# Where a base name is the subject rather than a leak: the registry itself, the
# card of that base, and the document describing the environments.
BASE_NAME_HOMES = ("config/1c-projects.tsv", "docs/operations/ENVIRONMENT_REGISTRY.md",
                   "configurations/")
# Identifiers too short or too common to mean a base: "erp" in a sentence is not
# a leak, and a one-letter id would fire on everything.
MINIMUM_NAME = 4


def base_names(root: Path) -> set[str]:
    """The working base identities this tree knows about.

    The standard's own registry is empty by definition, so in this repository
    the set is empty and the check is vacuous — which is exactly why it also
    runs against a created project, where the registry is filled in. The names
    have to come from somewhere real; inventing a list of plausible ones would
    check nothing.
    """
    path = root / REGISTRY
    if not path.is_file():
        return set()
    lines = path.read_bytes().decode("utf-8", errors="replace").splitlines()
    if len(lines) < 2:
        return set()
    header = lines[0].split("\t")
    wanted = [header.index(column) for column in ("project_id", "environment_id", "configuration")
              if column in header]
    names: set[str] = set()
    for line in lines[1:]:
        values = line.split("\t")
        for index in wanted:
            if index < len(values):
                name = values[index].strip()
                if len(name) >= MINIMUM_NAME:
                    names.add(name)
    return names


def scan_names(text: str, names: set[str]) -> list[tuple[str, str, int, str]]:
    """Where a real base name appears outside the files that are about it."""
    found = []
    for number, line in enumerate(text.splitlines(), start=1):
        if MARKER.search(line):
            continue
        for name in names:
            if re.search(rf"(?<![0-9a-zA-Z_-]){re.escape(name)}(?![0-9a-zA-Z_-])", line):
                found.append(("name.base", f"the name of a working base '{name}'",
                              number, line.strip()[:120]))
                break
    return found


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(DEFAULT_ROOT),
                        help="tree to scan; a project created from the templates is scanned the same way")
    arguments = parser.parse_args()
    ROOT = Path(arguments.root).resolve()

    names = base_names(ROOT)
    for path in scanned_files(ROOT):
        try:
            text = path.read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            # Not text: a regular expression over lines would find nothing in it
            # anyway, and failing the build here would say nothing actionable.
            continue
        relative = path.relative_to(ROOT).as_posix()
        findings = list(scan(text))
        if names and not any(relative.startswith(home) for home in BASE_NAME_HOMES):
            findings.extend(scan_names(text, names))
        for code, description, number, line in findings:
            failures.append(f"{relative}:{number} [{code}] {description}: {line}")

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
        (r"C:\Users\ivan.petrov\AppData\Roaming\1C", "path.home"),  # noscan
        (r"base=D:\Users\admin\bases\erp", "path.home"),  # noscan
        ("C:\\\\Users\\\\ivan\\\\erp", "path.home"),  # noscan
        ("password: hunter2xyz # prod", "secret.assigned"),  # noscan
    )
    for line, expected in samples:
        codes = {code for code, _, _, _ in scan(line)}
        if expected not in codes:
            failures.append(f"the scanner misses '{line}': expected {expected}, got {codes or 'nothing'}")

    # A comment on the line must not switch the checks off.
    for line, expected in (
        ('ONEC_API_TOKEN = "ghp_realSecretValue1234567890abcd"  # example of a token', "secret.token"),  # noscan
        ('password: "S3cretRealValue"  # пример', "secret.assigned"),  # noscan
        ("ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789", "secret.token"),  # noscan
        ("AKIAIOSFODNN7EXAMPLE", "secret.token"),  # noscan
    ):
        codes = {code for code, _, _, _ in scan(line)}
        if not codes:
            failures.append(f"a comment must not silence the scanner: '{line}' gave nothing")

    for line in ("PASSWORD=<PASSWORD>", "DEFAULT_PASSWORD=", "путь вида /Users/<user>/project",
                 "рабочая папка раннера /home/runner/work/project",
                 "слово noscanner не выключает проверку: PASSWORD=<PASSWORD>",
                 "tokens = [token[1:-1] for token in split(command)]",
                 "token_option = arguments.token_option"):
        if scan(line):
            failures.append(f"the scanner must not fire on '{line}'")

    # The base-name check has to be exercised where names exist: this repository
    # ships an empty registry on purpose, so without a fixture the code would be
    # dead and the criterion would be a claim.
    with tempfile.TemporaryDirectory() as raw:
        fixture = Path(raw)
        (fixture / "config").mkdir()
        (fixture / REGISTRY).write_bytes(
            ("project_id\tenvironment_id\tconfiguration\n"
             "torgovlya-nord\tprod-main\tUpravlenieTorgovlei\n").encode("utf-8"))
        found = base_names(fixture)
        if "torgovlya-nord" not in found or "prod-main" not in found:
            failures.append(f"the registry must supply the names to look for: {found}")
        if any(len(name) < MINIMUM_NAME for name in found):
            failures.append(f"a name too short to mean a base must not be looked for: {found}")
        leak = scan_names("см. базу torgovlya-nord в примере", found)
        if not leak:
            failures.append("a working base name in a template must be a finding")
        if scan_names("см. базу torgovlya-nord-2 и torgovlya", found):
            failures.append("a longer or shorter word must not be mistaken for the name")
        if scan_names("см. базу torgovlya-nord  # noscan", found):
            failures.append("the marker must silence the base-name check as well")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        print(f"{len(failures)} secret scan finding(s).", file=sys.stderr)
        raise SystemExit(1)

    print(f"No secrets or machine paths found in {ROOT}.")
