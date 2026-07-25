---
type: research
status: deferred
owner: project
last_verified: 2026-07-25
source_of_truth: repository
related:
  - "[[INDEX]]"
  - "[[docs/README]]"
  - "[[docs/architecture/ONE_C_CAPABILITY_PLAN]]"
---

# Общий skill `transcribe`: сохранённый план доработки

## Решение о границе

`transcribe` не входит в capability `1c`, её release, зависимости и критерии
готовности. Два upstream-файла из `comol/ai_rules_1c` остаются учтённым
источником будущего общего skill:

- `content/skills/transcribe/SKILL.md`;
- `content/skills/transcribe/scripts/transcribe.py`.

Исходная точка — commit
`1b6e2ed089d45740672619e27548ee8ed88347c3`. Целевой владелец — общий слой для
не-1С проектов, а не capability `1c`; 1С-проект не получает skill автоматически.
Точный профиль поставки, opt-in/opt-out и возможная глобальная доступность
будут решены при возврате к этому плану. До отдельного решения реализацию не
начинать.

## Сохраняемый пользовательский контракт

- Назначение и имя `transcribe`.
- Обычная транскрибация, протокол встречи и анализ видеоинтерфейса.
- Параметры `--output-dir`, `--with-summary`, `--analyze-ui`, `--format`.
- Результаты:

```text
Transcript/<name>/
├── <name> - transcript.md
├── <name> - summary.md
├── <name> - detailed.md
└── screenshots/
```

Документированные английские имена становятся каноническими; текущие русские
имена скрипта не сохраняются как второй контракт.

## Предлагаемая реализация

1. Основной backend — локальный Whisper, предварительно рекомендуется
   `faster-whisper`: CPU `int8`, модель `small` по умолчанию, возможность
   явного выбора другой модели.
2. Медиа не загружается в Gemini или другой отдельный transcription API.
   Обычная транскрибация не требует API key и поминутной оплаты.
3. Summary создаёт текущий AI-клиент по готовому transcript; исходное
   аудио/видео ему для этого не передаётся.
4. `--analyze-ui` локально извлекает кадры, после чего текущий multimodal
   AI-клиент анализирует transcript и screenshots. Перед передачей изображений
   пользователю явно сообщается о внешней обработке.
5. Базовый skill не выдумывает speaker labels: Whisper не даёт надёжной
   diarization. Отдельный diarization-компонент можно рассмотреть позже как
   optional dependency.
6. Для локального backend прежняя часовая Gemini-разбивка не используется.
   Любая остающаяся media/frame operation проверяет exit code и непустой
   результат; временные файлы очищаются в `finally`.
7. Outputs пишутся атомарно. Ошибка decode/model/frame extraction не может
   завершиться сообщением об успехе или пустой «готовой» транскрипцией.

## Зависимости и поставка

- Python 3.9+.
- Pinned/tested `faster-whisper` и транзитивные зависимости в project-local
  virtualenv; установка только с разрешения.
- Локально кэшируемая модель Whisper; первый download сообщается отдельно и
  не считается отправкой пользовательского медиа.
- FFmpeg требуется только для функций извлечения кадров/анализа UI, если
  выбранный backend декодирует обычное медиа через PyAV.
- GPU/CUDA — отдельная optional-конфигурация; безопасный default — CPU.
- Отсутствие skill или его зависимостей не блокирует создание и обычную работу
  проекта.

Будущий общий doctor должен показывать Python, backend/version, model cache,
CPU/GPU mode и FFmpeg для UI-режима. Пользовательская документация обязана
назвать зависимости и отдельно объяснить локальную обработку, model download
и передачу transcript/screenshots текущему AI-клиенту.

## Открытые решения перед реализацией

1. Подтвердить `faster-whisper` вместо официального `openai-whisper`.
2. Подтвердить модель `small` и CPU `int8` как defaults.
3. Определить точный набор project profiles и opt-in/opt-out общего skill.
4. Определить форму disclosure/confirmation для summary и анализа кадров.
5. Решить, нужен ли позже отдельный diarization backend.

## Обязательные проверки

- audio/video fixtures, тишина, повреждённый файл и длинная запись;
- timestamp monotonicity и canonical output names;
- отсутствие network media upload в default flow;
- model-download disclosure и offline cached run;
- atomic outputs и cleanup после ошибок;
- frame extraction fail-closed;
- summary/UI flow не создаёт результатов без обязательных исходных artifacts;
- Codex/Claude discovery и одинаковый пользовательский контракт.

Связанные открытые дефекты: №101–104 в
[[docs/quality/DEFECTS|реестре дефектов]].
