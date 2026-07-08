---
type: research
status: complete
owner: project
last_verified: 2026-07-07
source_of_truth: repository
related:
  - "[[docs/architecture/decisions/ADR-0003-two-tier-knowledge-architecture]]"
  - "[[docs/research/NPR_BP_KNOWLEDGE_ARCHITECTURE_2026-07-06]]"
  - "[[docs/quality/DEFECTS]]"
---

# Совместный harvest-анализ NPR и Best Practices — 2026-07-07

## Область и метод

Проведён единый read-only анализ двух связанных репозиториев:

- `NightMadMax/new-project-rules` (`Правила для нового проекта`, далее NPR);
- `NightMadMax/best-practices` (`Best Practices`, далее BP).

Проверялись фактические Git-деревья, роли документов, skills, scripts,
validators, tests, GitHub branches, открытые PR, последние Actions runs и
защита `main`. Ранее созданные исследования использовались только как контекст;
выводы повторно сверялись с текущей реализацией.

## Итоговое архитектурное заключение

Репозитории правильно разделены и не должны объединяться:

- **NPR — обязательная конституция:** структура проекта, baseline правил
  агентов, bootstrap, diagnostics, migrations, standardization и безопасность.
- **BP — развиваемая доказательная база:** технические и стековые практики,
  проходящие `harvest → review → delivery`.

Канонический пользовательский обратный поток должен быть единственным:

1. проектный сигнал остаётся в `DEFECTS`, `PLAYBOOK`, ADR или research проекта;
2. `harvest-practice-candidates` нормализует повторяемый урок в BP;
3. `review-practice-candidates` принимает или отклоняет его;
4. `apply-best-practices` доставляет accepted-практику в проекты;
5. только администратор может затвердить вызревшую BP-практику в NPR через
   `promote-project-knowledge → apply-promotion-candidate`.

Модель соответствует [[docs/architecture/decisions/ADR-0003-two-tier-knowledge-architecture|ADR-0003]],
но пока не удерживается единым исполняемым cross-repository контрактом.

## Функциональная карта

| Контур | NPR | BP |
|---|---|---|
| Создание | bootstrap профилей и metadata | создание practice candidate |
| Проверка | validator, doctor, contract и environment checks | schema, provenance, secrets, lifecycle и freshness |
| Изменение | fingerprinted migrations и standardization | review candidate и lifecycle practice |
| Доставка | template/skill/global policy в проекты | accepted practice в consumer project |
| Обратная связь | maintainer-only затвердевание | пользовательский harvest через PR |
| Метрики | корректность стандарта и migration safety | maturity, consumer outcomes и adoption rate |

## Подтверждённые сильные стороны

### NPR

- Manifest-driven профили и parity shell/PowerShell.
- Безопасные read-only assessment/plan режимы и fingerprinted apply.
- Symlink, containment, stale-preimage и supply-chain guards.
- Managed/unmanaged модель правил сохраняет локальные инструкции проекта.
- Полный локальный прогон 2026-07-07: 150 bootstrap checks, 47 agent setup
  checks, skill checks, validator/migration/standardization/compression/
  supply-chain suites; итог `0 error(s), 0 warning(s)`.
- Последние GitHub Actions для `main` успешны на `ci` и `macos-smoke`.

### Best Practices

- Один файл на candidate/practice, collision-resistant ID и сохранение истории.
- Provenance, evidence levels, lifecycle и freshness формализованы и
  проверяются validator.
- Whole-repository secret scan и проверка machine-specific paths.
- Search/catalog, applicability report и consumer outcome metrics.
- На ветке `codex/p1-trust-hardening` 41 test и обе validator-проверки прошли.
- `main` защищён активным GitHub ruleset.

## Findings

### P0. `new-project-rules/main` не защищён

GitHub API вернул `Branch not protected`, список repository rulesets пуст.
Это противоречит maintainer-only модели: наиболее чувствительный репозиторий
можно менять прямым push, тогда как BP защищён.

### P0. Усиленная версия BP не доставлена потребителям

Рабочая ветка `codex/p1-trust-hardening` на 12 коммитов опережает
`origin/main`, открытого PR нет. Локально анализируется зрелая версия с
lifecycle invariants, metrics и catalog, но clone/pull `main` получает более
слабый контракт.

### P1. BP ссылается на удалённый `harvest-project-lessons`

Устаревший маршрут остаётся в `README.md` и
`.agents/skills/harvest-practice-candidates/SKILL.md`. В NPR skill отсутствует и
намеренно удалён фазой 2 ADR-0003. Это пользовательский dead end и признак
отсутствия cross-repo contract test.

### P1. Нет исполняемого cross-repository контракта

Оба репозитория хорошо тестируют себя по отдельности, но автоматически не
проверяются:

- существование упомянутых skills и маршрутов соседнего проекта;
- допустимость и статус исходной BP-практики для promotion в NPR;
- закреплённый source commit и воспроизводимость provenance;
- совместимость версий NPR/BP;
- отсутствие устаревших ссылок после изменения одного репозитория.

### P1. Версия NPR не отражает изменение контракта

Фазы managed project baseline и двухъярусной knowledge architecture находятся
в `main` и `CHANGELOG.md`/`Unreleased`, но `STANDARD_VERSION` остаётся `1`.
ADR-0003 прямо требует version bump и migration entry при изменении шаблона и
состава skills.

### P2. Механика BP опережает полезное содержание

Метрики текущей ветки: один accepted candidate, одна accepted practice `common`
уровня `E2`, остальные разделы пусты. Из четырёх проверенных соседних consumer
projects ни один не содержит `.best-practices.json`; recorded decisions равны
нулю, adoption rate не вычисляется.

### P2. Сквозной SSOT пока держится соглашением

Для secrets, portability и tool selection ADR задаёт правильное разделение:
императив в NPR, evidence/rationale в BP. Однако мягкая ссылка не проверяется
машиной, поэтому изменения одного слоя могут оставить второй устаревшим.

## Оценка зрелости

| Контур | Оценка | Обоснование |
|---|---:|---|
| NPR bootstrap/validation/migration | 9/10 | Сильное regression и adversarial coverage |
| NPR governance | 5/10 | Нет защиты `main`, version transition не завершён |
| BP внутренняя модель | 8/10 | Строгая schema/lifecycle на feature branch |
| BP опубликованный `main` | 4/10 | 12 коммитов hardening не интегрированы |
| Cross-repo интеграция | 4/10 | Архитектура описана, общий контракт отсутствует |
| Наполнение BP | 2/10 | Одна accepted practice только в `common` |
| Измеренная ценность | 1/10 | Нет записанных consumer outcomes |

## Рекомендуемый порядок работ

1. Создать и проверить PR `codex/p1-trust-hardening → main` в BP.
2. Защитить `new-project-rules/main` ruleset'ом не слабее BP.
3. Удалить ссылки BP на `harvest-project-lessons` и закрепить актуальный маршрут.
4. Добавить cross-repo contract suite с fixture/pinned compatibility manifest.
5. Выпустить новую версию NPR с migration entry для managed baseline.
6. Провести harvest реальных проектов и наполнить BP как минимум разделами
   `common`, `tools`, `prompts` и релевантными stack practices.
7. Выполнить пилот применения минимум в двух consumer projects и записать
   outcomes в `.best-practices.json`.

## Критерии завершённой системы

Связку можно считать production-ready, когда:

- оба `main` защищены и проходят обязательный CI;
- BP hardening находится в `main`, а не только в feature branch;
- cross-repo suite ловит удалённый skill, stale route и несовместимую версию;
- NPR release/version/migration отражают текущий managed contract;
- BP содержит несколько независимо подтверждённых практик;
- минимум два consumer projects записали outcomes, и adoption rate измерим.
