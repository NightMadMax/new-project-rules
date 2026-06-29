---
type: decision
status: accepted
owner: project
last_verified: 2026-06-29
source_of_truth: repository
related:
  - "[[docs/architecture/ARCHITECTURE|ARCHITECTURE]]"
  - "[[docs/research/STRATEGIC_EVOLUTION_PLAN|STRATEGIC_EVOLUTION_PLAN]]"
  - "[[docs/quality/TESTING|TESTING]]"
  - "[[PROJECT]]"
---

# ADR-0002: Версионируемый контракт проекта

## Контекст

Состав профилей, обязательные policy blocks и index relationships сейчас
закодированы параллельно в shell-, PowerShell-скриптах, тестах и документации.
Regression tests проверяют каждую реализацию, но не задают независимый
машиночитаемый контракт и не позволяют определить версию стандарта.

Стратегический план предусматривает validator и migrations, которым необходимы
стабильная schema version и единое описание ожидаемого состояния.

## Решение

1. Хранить schema version стандарта в `STANDARD_VERSION` независимо от release
   version проекта.
2. Описывать состав профилей и index relationships в line-oriented TSV под
   `config/`. TSV читается POSIX shell и PowerShell без новых зависимостей.
3. На первом этапе считать manifest read-only contract fixture: bootstrap ещё
   не читает его, а parity tests сравнивают manifest с фактическим output обеих
   реализаций.
4. Сохранить native shell и PowerShell как zero-dependency bootstrap adapters.
5. Для будущих сложных validator и migrator использовать Python 3 standard
   library через native wrappers. Python не становится скрытым требованием
   базового bootstrap и не устанавливается без разрешения пользователя.
6. В будущих migrations по умолчанию строить read-only plan; mutation требует
   отдельного `--apply` и чистого git working tree.

## Последствия

- изменение состава профиля требует сначала изменить один contract fixture;
- CI обнаруживает расхождение fixture, shell и PowerShell до публикации;
- следующий этап сможет перевести bootstrap на manifest без одновременного
  изменения пользовательского output;
- schema migrations получают независимую от changelog версию;
- TSV ограничивает значения одной строкой без tab characters, что приемлемо
  для путей и boolean relationships;
- до manifest-driven refactor существует контролируемое временное дублирование:
  contract описывает поведение, а adapters всё ещё реализуют его вручную.
