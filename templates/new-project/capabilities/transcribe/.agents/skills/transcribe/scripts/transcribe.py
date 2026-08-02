#!/usr/bin/env python3
"""Transcribe an audio or video file locally, and never report success falsely.

The upstream version sent the file to an external transcription API. This one
does not: an ordinary transcription needs no API key, no per-minute billing and
no upload of somebody's meeting. The model runs on this machine, and the only
thing that ever leaves it is what the user asks a client to summarise.

Three failure modes shaped the code, and each of them once produced a green run
with nothing behind it:

* a media step whose exit code nobody checked wrote no output, and the caller
  reported a finished transcription that was empty;
* outputs were written as the work went, so an error halfway left files that
  looked complete;
* the documented names and the written names disagreed, so neither the user nor
  the next agent could tell which file was the result.

So: every external call is checked, an empty result is an error, outputs are
written atomically at the end, and the names come from one table.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

# The one place the result names are decided. The upstream script wrote Russian
# names while its own documentation promised English ones — a contract nobody
# could rely on, in either language.
# What this script writes, and nothing else. `summary` and `detailed` were
# listed here and never produced: the script has no summarizer, and the skill
# says plainly that the AI client writes the summary from the finished
# transcript. Declaring outputs nobody writes made the contract unusable in the
# other direction — a caller waiting for three files waits forever.
#
# The suffix follows --format, because a JSON document written into a .md name
# is a file no tool opens correctly.
OUTPUTS = {"transcript": "{name} - transcript.{suffix}"}
OUTPUT_DIRECTORY = "Transcript"
SCREENSHOTS = "screenshots"
FORMATS = ("md", "txt", "json")
DEFAULT_MODEL = "small"
DEFAULT_COMPUTE = "int8"
FRAME_INTERVAL_SECONDS = 30
PROBE_TIMEOUT_SECONDS = 60
FRAME_TIMEOUT_SECONDS = 600


class TranscribeError(Exception):
    """The run cannot produce a result, and this says why."""


@dataclass
class Segment:
    start: float
    end: float
    text: str


@dataclass
class Transcription:
    segments: list[Segment] = field(default_factory=list)
    language: str = ""
    model: str = ""

    @property
    def text(self) -> str:
        return "\n".join(segment.text.strip() for segment in self.segments if segment.text.strip())


def timestamp(seconds: float) -> str:
    seconds = max(0, int(seconds))
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def check_monotonic(segments: list[Segment]) -> None:
    """Time must move forward. A model that repeats itself produces overlapping
    segments, and a transcript assembled from them silently loses text."""
    previous = -1.0
    for segment in segments:
        if segment.start < previous - 0.001 or segment.end < segment.start - 0.001:
            raise TranscribeError(
                f"таймкоды не возрастают: {timestamp(segment.start)}–{timestamp(segment.end)} "
                f"после {timestamp(previous)}"
            )
        previous = segment.start


def load_backend(model: str, compute: str):
    """The local model, or a refusal that names what to install.

    Imported here rather than at module load: the skill ships with the project,
    and importing a heavy optional dependency at import time would make every
    other use of this file fail on a machine that never asked for it.
    """
    try:
        from faster_whisper import WhisperModel  # noqa: PLC0415
    except ImportError as error:
        raise TranscribeError(
            "faster-whisper не установлен: это условная зависимость skill. "
            "Установка — с разрешения пользователя, в project-local окружение."
        ) from error
    return WhisperModel(model, device="cpu", compute_type=compute)


def transcribe(source: Path, *, model: str = DEFAULT_MODEL, compute: str = DEFAULT_COMPUTE,
               backend=None) -> Transcription:
    """The transcription, or an error. Never an empty success."""
    if not source.is_file():
        raise TranscribeError(f"файл не найден: {source}")
    engine = load_backend(model, compute) if backend is None else backend
    raw, info = engine.transcribe(str(source))
    segments = [Segment(float(item.start), float(item.end), str(item.text)) for item in raw]
    if not segments:
        # Silence and a failed decode look identical from here, and both mean
        # there is no transcript. Writing an empty file and reporting success is
        # how a broken run becomes a finished one.
        raise TranscribeError(
            f"распознавание не дало ни одного сегмента: {source.name} — "
            "файл пуст, состоит из тишины или не декодируется"
        )
    check_monotonic(segments)
    return Transcription(segments, getattr(info, "language", ""), model)


def render(result: Transcription, name: str, fmt: str = "md") -> str:
    if fmt not in FORMATS:
        raise TranscribeError(f"неизвестный формат '{fmt}'; допустимы {', '.join(FORMATS)}")
    if fmt == "txt":
        return result.text + "\n"
    if fmt == "json":
        return json.dumps({
            "name": name,
            "language": result.language,
            "model": result.model,
            "segments": [{"start": item.start, "end": item.end, "text": item.text.strip()}
                         for item in result.segments],
        }, ensure_ascii=False, indent=2) + "\n"
    lines = [f"# {name}", "",
             f"Язык: {result.language or 'не определён'}. Модель: {result.model}. "
             "Распознавание выполнено локально.", ""]
    for segment in result.segments:
        lines.append(f"**[{timestamp(segment.start)}]** {segment.text.strip()}")
    return "\n".join(lines) + "\n"


def run(command: list[str], timeout: int) -> tuple[int, str]:
    try:
        completed = subprocess.run(command, capture_output=True, timeout=timeout, check=False)
    except FileNotFoundError as error:
        raise TranscribeError(f"{command[0]} не найден: {error.strerror or error}") from error
    except subprocess.TimeoutExpired as error:
        raise TranscribeError(f"{command[0]} не ответил за {timeout} с") from error
    output = (completed.stdout or b"") + (completed.stderr or b"")
    return completed.returncode, output.decode("utf-8", errors="replace")


def extract_frames(source: Path, destination: Path, *, interval: int = FRAME_INTERVAL_SECONDS,
                   runner=run) -> list[Path]:
    """Frames for UI analysis, or an error. A zero exit code is not the check.

    Defect 104 lived here: ffmpeg failed, no file was written, the caller took
    the empty list for "a video without frames" and finished successfully.
    """
    destination.mkdir(parents=True, exist_ok=True)
    code, output = runner(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(source),
         "-vf", f"fps=1/{interval}", str(destination / "frame-%04d.png")],
        FRAME_TIMEOUT_SECONDS,
    )
    if code != 0:
        raise TranscribeError(f"ffmpeg завершился с кодом {code}: {output.strip()[:200]}")
    frames = sorted(destination.glob("frame-*.png"))
    if not frames:
        raise TranscribeError("ffmpeg завершился успешно, но не создал ни одного кадра")
    return frames


def write_atomically(files: dict[Path, str]) -> None:
    """All results appear together or none of them do.

    Written as the work went, a partial set is indistinguishable from a complete
    one: the names are right, the content is half a run. Renaming can fail too —
    a file held open, a name that is a directory — so what has already landed is
    undone rather than left as a half-written set with the right names.
    """
    staged: list[tuple[Path, Path]] = []
    replaced: list[tuple[Path, bytes | None]] = []
    try:
        for path, content in files.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            handle, staging = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".",
                                               suffix=".part")
            os.close(handle)
            Path(staging).write_bytes(content.encode("utf-8"))
            staged.append((Path(staging), path))
        for staging, path in staged:
            replaced.append((path, path.read_bytes() if path.is_file() else None))
            staging.replace(path)
    except BaseException:
        for path, previous in reversed(replaced):
            # The rollback must not fail on its own: an entry that cannot be
            # undone is one file left behind, while an exception here would
            # abandon every other file that still can be.
            try:
                if previous is None:
                    if path.is_file():
                        path.unlink()
                else:
                    path.write_bytes(previous)
            except OSError:
                continue
        raise
    finally:
        for staging, _ in staged:
            if staging.exists():
                staging.unlink()


def output_paths(root: Path, name: str, fmt: str = "md") -> dict[str, Path]:
    if fmt not in FORMATS:
        raise TranscribeError(f"неизвестный формат '{fmt}'; допустимы {', '.join(FORMATS)}")
    directory = root / OUTPUT_DIRECTORY / name
    return {key: directory / pattern.format(name=name, suffix=fmt)
            for key, pattern in OUTPUTS.items()}


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="аудио или видео файл")
    parser.add_argument("--output-dir", default=".", help="куда положить каталог Transcript")
    parser.add_argument("--with-summary", action="store_true",
                        help="подготовить место для summary; сам текст пишет AI-клиент по transcript")
    parser.add_argument("--analyze-ui", action="store_true",
                        help="извлечь кадры для анализа интерфейса (нужен ffmpeg)")
    parser.add_argument("--format", default="md", choices=FORMATS)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--compute", default=DEFAULT_COMPUTE)
    arguments = parser.parse_args(argv)

    source = Path(arguments.source).expanduser()
    name = source.stem
    root = Path(arguments.output_dir).expanduser().resolve()
    paths = output_paths(root, name, arguments.format)
    frames_directory = paths["transcript"].parent / SCREENSHOTS

    try:
        result = transcribe(source, model=arguments.model, compute=arguments.compute)
        files = {paths["transcript"]: render(result, name, arguments.format)}
        frames: list[Path] = []
        if arguments.analyze_ui:
            frames = extract_frames(source, frames_directory)
        write_atomically(files)
    except TranscribeError as error:
        # Nothing has been written by this point: the outputs land in one step
        # after everything that can fail has succeeded.
        if frames_directory.is_dir() and not any(frames_directory.iterdir()):
            shutil.rmtree(frames_directory, ignore_errors=True)
        print(f"[ERROR] {error}", file=sys.stderr)
        return 1

    print(f"[OK] {paths['transcript']}")
    if arguments.analyze_ui:
        print(f"[OK] кадров: {len(frames)} — {frames_directory}")
        print("Кадры и transcript передаются текущему AI-клиенту — это внешняя обработка.")
    if arguments.with_summary:
        print(f"Summary пишет AI-клиент по готовому transcript в {paths['summary']}; "
              "исходное медиа ему не передаётся.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
