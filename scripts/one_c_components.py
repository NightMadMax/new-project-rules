#!/usr/bin/env python3
"""The component catalog and the question asked about each component.

Until now the catalog was a table in a subplan: a person could read it, nothing
could check it. A prompt assembled by hand drops exactly the fields that are
inconvenient to write — what breaks if you refuse, whether it needs admin, where
the official source is — and those are the fields the decision rests on. So the
catalog is data, the prompt is built from it, and a row missing a field is an
error rather than a shorter question.

Three classes carry different consequences and are never merged: skipping a
`required` component makes the environment `incomplete`, skipping a
`conditional` one disables named features, skipping an `optional` one costs
nothing. That difference is the whole reason the class column exists.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

CATALOG = "config/1c-components.tsv"
COLUMNS = (
    "component", "class", "purpose", "enables", "consequence", "version",
    "download", "docs", "install", "command", "prerequisites", "admin", "restart",
    "network", "credentials", "license", "platform", "detect",
)
# `command` is the only optional cell: most components are installed by a vendor
# installer that no command of ours may stand in for.
OPTIONAL_COLUMNS = ("command",)
CLASSES = ("required", "conditional", "optional")
INSTALL_MODES = ("automatic", "assisted", "manual", "project-local", "reuse")
DETECT_SCHEMES = ("cli", "runtime", "python", "node", "env", "provider", "manual")
FLAGS = ("admin", "restart", "network", "credentials", "license")
PLATFORMS = ("any", "windows")

# The three options are the contract of the interactive step: a component is
# either installed for the user, installed by the user, or consciously left out.
# A prompt with two options quietly makes one of those the default.
MISSING_OPTIONS = ("установить автоматически", "установить самостоятельно", "пропустить")
FOUND_OPTIONS = ("использовать", "обновить или переустановить", "не использовать")

# Every label the prompt has to carry. The test checks the labels rather than the
# text, because the text is where a field silently loses its meaning.
PROMPT_FIELDS = (
    "Компонент", "Класс", "Назначение", "Включает", "Последствия отказа",
    "Версия", "Источник", "Документация", "Установка", "Требуется заранее",
    "Права администратора", "Перезагрузка", "Сеть", "Учётные данные", "Лицензия",
    "Варианты",
)
YES_NO = {"yes": "да", "no": "нет"}


class CatalogError(Exception):
    """The catalog cannot be used as it stands, and this says why."""


@dataclass(frozen=True)
class Component:
    values: dict[str, str]

    def __getattr__(self, name: str) -> str:
        try:
            return self.values[name]
        except KeyError as error:  # pragma: no cover - attribute typo
            raise AttributeError(name) from error

    @property
    def name(self) -> str:
        return self.values["component"]

    @property
    def component_class(self) -> str:
        return self.values["class"]

    @property
    def scheme(self) -> str:
        return self.values["detect"].split(":", 1)[0]

    @property
    def target(self) -> str:
        _, _, target = self.values["detect"].partition(":")
        return target


def load(root: Path, relative: str = CATALOG) -> list[Component]:
    path = root / relative
    try:
        # `utf-8-sig` because an editor on Windows adds a BOM without asking,
        # and the first column name would then never match.
        lines = path.read_bytes().decode("utf-8-sig").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        raise CatalogError(f"{relative} is unreadable: {error}") from error
    if not lines:
        raise CatalogError(f"{relative} is empty")
    header = lines[0].split("\t")
    if tuple(header) != COLUMNS:
        raise CatalogError(f"{relative} header is {header}, expected {list(COLUMNS)}")

    components: list[Component] = []
    seen: set[str] = set()
    for number, line in enumerate(lines[1:], start=2):
        if not line.strip():
            continue
        values = line.split("\t")
        if len(values) != len(COLUMNS):
            raise CatalogError(f"{relative}:{number} has {len(values)} fields against {len(COLUMNS)}")
        row = dict(zip(COLUMNS, values))
        where = f"{relative}:{number}"
        for column in COLUMNS:
            if column not in OPTIONAL_COLUMNS and not row[column].strip():
                raise CatalogError(f"{where}: '{column}' is empty; the prompt would drop the field")
        if row["class"] not in CLASSES:
            raise CatalogError(f"{where}: unknown class '{row['class']}'")
        if row["install"] not in INSTALL_MODES:
            raise CatalogError(f"{where}: unknown install mode '{row['install']}'")
        if row["detect"].split(":", 1)[0] not in DETECT_SCHEMES:
            raise CatalogError(f"{where}: unknown detect scheme '{row['detect']}'")
        if row["platform"] not in PLATFORMS:
            raise CatalogError(f"{where}: unknown platform '{row['platform']}'")
        for flag in FLAGS:
            if row[flag] not in YES_NO:
                raise CatalogError(f"{where}: '{flag}' must be yes or no, not '{row[flag]}'")
        # An automatic option with nothing to run would be answered by silence.
        if row["install"] in ("automatic", "project-local") and not row["command"].strip():
            raise CatalogError(f"{where}: install '{row['install']}' promises a command and names none")
        if row["component"] in seen:
            raise CatalogError(f"{where}: '{row['component']}' is declared twice")
        seen.add(row["component"])
        components.append(Component(row))
    if not components:
        raise CatalogError(f"{relative} declares no components")
    return components


def options(component: Component, found: bool) -> list[str]:
    """The three answers, with the unavailable one saying why.

    Removing the automatic option where there is no command would leave two
    answers and hide the reason; offering it anyway would promise an install
    that cannot run.
    """
    if found:
        return list(FOUND_OPTIONS)
    if component.scheme == "manual":
        # There is no machine check for this one, so "not found" only means
        # "not measured". Without this answer a required component like the
        # platform itself could never leave the skipped set, and a fully
        # configured machine would never reach `ready`.
        return [f"{FOUND_OPTIONS[0]} — подтвердить, что установлено: "
                "машинной проверки у этого компонента нет",
                *MISSING_OPTIONS[1:]]
    if component.command.strip():
        automatic = f"{MISSING_OPTIONS[0]}: {component.command}"
    else:
        automatic = (f"{MISSING_OPTIONS[0]} — недоступно: установка идёт способом "
                     f"'{component.install}', команды у неё нет")
    return [automatic, *MISSING_OPTIONS[1:]]


def prompt(component: Component, found: bool = False, detail: str = "") -> str:
    """Everything the answer depends on, in one block, before the question."""
    lines = [
        f"Компонент: {component.name}",
        f"Класс: {component.component_class}",
        f"Назначение: {component.purpose}",
        f"Включает: {component.enables}",
        f"Последствия отказа: {component.consequence}",
        f"Версия: {component.version}" + (f" (обнаружено: {detail})" if detail else ""),
        f"Источник: {component.download}",
        f"Документация: {component.docs}",
        f"Установка: {component.install}" + (f" — {component.command}" if component.command.strip() else ""),
        # What has to be there first. Without this the user meets a component
        # that simply refuses to install and no line says why: Docker on a clean
        # Windows is the standing example.
        f"Требуется заранее: {component.prerequisites}",
        f"Права администратора: {YES_NO[component.admin]}",
        f"Перезагрузка: {YES_NO[component.restart]}",
        f"Сеть: {YES_NO[component.network]}",
        f"Учётные данные: {YES_NO[component.credentials]}",
        f"Лицензия: {YES_NO[component.license]}",
        "Варианты: " + "; ".join(options(component, found)),
    ]
    return "\n".join(lines)


TABLE_BEGIN = "<!-- generated from config/1c-components.tsv -->"
TABLE_END = "<!-- /generated -->"


def render_table(components: list[Component]) -> str:
    """The subplan's table, built from the catalog.

    Two hand-kept lists of components are two answers to what `required` means,
    and they had already drifted: the prose promised an automatic install for
    seven components the catalog gives no command for. So the table is derived
    and the check is exact, rather than a search for a word.
    """
    lines = [TABLE_BEGIN,
             "",
             "| Компонент | Класс | Зачем | Установка | Требуется заранее | Результат пропуска |",
             "|---|---|---|---|---|---|"]
    for item in components:
        install = item.install if not item.command.strip() else f"{item.install}: `{item.command}`"
        source = f"<{item.download}>" if item.download.startswith("http") else f"`{item.download}`"
        lines.append(f"| {item.name} | {item.component_class} | {item.purpose} | "
                     f"{install}; {source} | {item.prerequisites} | {item.consequence} |")
    lines.extend(["", TABLE_END])
    return "\n".join(lines)


def outcome(components: list[Component], skipped: set[str]) -> dict[str, object]:
    """What the environment is after the answers, in the plan's own terms."""
    required = [item.name for item in components
                if item.component_class == "required" and item.name in skipped]
    disabled = [f"{item.name}: {item.consequence}" for item in components
                if item.component_class == "conditional" and item.name in skipped]
    return {
        "status": "incomplete" if required else "ready",
        "skipped_required": required,
        "disabled_features": disabled,
        # Named separately so that "it does not affect the status" is a fact of
        # the report rather than a claim in a document.
        "skipped_optional": [item.name for item in components
                             if item.component_class == "optional" and item.name in skipped],
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--standard-root", default=".", help="checkout of new-project-rules")
    parser.add_argument("--class", dest="component_class", choices=CLASSES,
                        help="show only one class")
    parser.add_argument("--table", action="store_true",
                        help="таблица каталога для подплана среды")
    arguments = parser.parse_args(argv)
    try:
        components = load(Path(arguments.standard_root).resolve())
    except CatalogError as error:
        print(f"[ERROR] {error}", file=sys.stderr)
        return 2
    if arguments.table:
        print(render_table(components))
        return 0
    for component in components:
        if arguments.component_class and component.component_class != arguments.component_class:
            continue
        print(prompt(component))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
