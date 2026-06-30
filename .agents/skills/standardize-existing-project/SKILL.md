---
name: standardize-existing-project
description: Анализирует уже существующий проект и предлагает безопасную стратегию приведения к стандарту new-project-rules: изменить текущий repo на месте или создать новый проект по правилам на основе существующего. Использовать, когда пользователь просит привести legacy-проект к шаблону, оценить возможность adoption in place или пересобрать проект по стандарту без слепого bootstrap поверх существующего дерева.
---

# Стандартизация существующего проекта

Этот skill не должен дублировать assessment-логику. Сначала он обязан вызвать
workflow `assess-existing-project`, а затем использовать его результат для
выбора и выполнения стратегии стандартизации.

## Найти источник правил

1. Найти корень `new-project-rules`: каталог должен содержать `AGENTS.md`,
   `docs/guides/`, `templates/new-project/` и `scripts/`.
2. Полностью прочитать корневой `AGENTS.md`,
   `docs/guides/ASSESS_EXISTING_PROJECT.md`,
   `docs/guides/STANDARDIZE_EXISTING_PROJECT.md`,
   `docs/guides/VALIDATE_AND_DIAGNOSE.md`,
   `docs/guides/PLAN_MIGRATIONS.md` и, если понадобится создание нового repo,
   `docs/guides/CREATE_NEW_PROJECT.md`. Эти файлы имеют приоритет над skill.

## Определить параметры

1. Получить путь к существующему проекту.
2. Если стратегия не указана, начать с `assess-existing-project` и не менять
   файлы до выбора пользователем.
3. Если профиль не указан, попытаться определить `candidate_profile`, но не
   угадывать его при неоднозначном дереве.
4. Если выбран вариант `re-bootstrap-from-existing`, получить путь назначения,
   имя нового проекта, профиль и visibility GitHub repository.

## Использовать assessment

1. Сначала выполнить `assess-existing-project`.
2. Получить decision report без изменения файлов.
3. Если assessment уже показывает `blocked` или `manual_review_required`,
   сообщить это пользователю и не переходить к risky apply без явного решения.
4. Не повторять ту же read-only логику вручную, если assessment уже доступен.

## Strategy A: adopt-in-place

1. Работать консервативно: не запускать bootstrap поверх существующего дерева.
2. Можно автоматически создавать только отсутствующие безопасные managed files:
   `CLAUDE.md`, `.gitignore`, `.gitattributes`, `.editorconfig`,
   `docs/README.md` при отсутствии.
3. `INDEX.md` и `docs/README.md` обновлять только добавлением недостающих
   wikilinks и только после review текущего содержимого.
4. Не перезаписывать существующие `README.md`, `PROJECT.md`, `AGENTS.md` без
   явного согласования с пользователем.
5. Для review сначала строить apply-plan:
   - macOS/Linux: `./scripts/standardize-existing-project.sh --root <target> --strategy adopt-in-place --plan-adopt`;
   - Windows: `.\scripts\standardize-existing-project.ps1 -Root <target> -Strategy adopt-in-place -PlanAdopt`.
6. Применять только через fingerprint и явное подтверждение:
   - macOS/Linux: `./scripts/standardize-existing-project.sh --root <target> --strategy adopt-in-place --apply --fingerprint <value> --yes`;
   - Windows: `.\scripts\standardize-existing-project.ps1 -Root <target> -Strategy adopt-in-place -Apply -Fingerprint <value> -Confirm`.
7. После apply прогнать validator.
8. Metadata adoption делать только через:
   - macOS/Linux: `./scripts/plan-migration.sh --plan --target project ...`;
   - Windows: `.\scripts\plan-migration.ps1 -Plan -Target project ...`.
   Применять только по подтверждённому fingerprint. Не создавать
   `.project-standard.json` вручную.

## Strategy B: re-bootstrap-from-existing

1. Создать новый проект отдельной папкой и отдельным repo; не разрушать legacy
   проект.
2. Для создания нового repo использовать канонический workflow
   `create-new-project`.
3. По умолчанию переносить только согласованный safe set: код, тесты,
   manifests, безопасные configs, выбранные docs.
4. Не переносить автоматически secrets, `.env*`, deployment credentials,
   старые agent instructions и сомнительные CI/workflow files.
5. После переноса прогнать validator и metadata adoption уже для нового repo.
6. Явно перечислить, что осталось в legacy project и что не было перенесено.

## Общие ограничения

1. Перед установкой отсутствующего инструмента объяснить необходимость и
   получить разрешение пользователя.
2. При dirty tree не выполнять risky apply без явного согласования.
3. При конфликтующем `CLAUDE.md`, `AGENTS.md`, nested `.obsidian`, symlink в
   managed destinations или неоднозначном profile переводить workflow в
   `manual_review_required` или `blocked`.
4. Не объявлять проект стандартизированным, пока validator не пройден и
   migration status не подтверждён.
5. Первая реализация apply покрывает только safe `adopt-in-place`; сложный
   merge docs и `re-bootstrap-from-existing` остаются orchestration-only.
