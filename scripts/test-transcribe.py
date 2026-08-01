#!/usr/bin/env python3
"""A transcription run must not be able to report success falsely.

Four defects (№101–№104) all had the same shape: a run that produced nothing, or
half of something, and finished as if it had worked. So every check here is
about the difference between a result and the appearance of one.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
SKILL = ROOT / "templates/new-project/capabilities/transcribe/.agents/skills/transcribe"

spec = importlib.util.spec_from_file_location("transcribe", SKILL / "scripts/transcribe.py")
assert spec and spec.loader
transcribe = importlib.util.module_from_spec(spec)
sys.modules["transcribe"] = transcribe
spec.loader.exec_module(transcribe)

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

failures: list[str] = []


def note(condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


class Piece:
    def __init__(self, start: float, end: float, text: str):
        self.start, self.end, self.text = start, end, text


class Info:
    language = "ru"


class Engine:
    """A backend that answers with what the test wants it to answer."""

    def __init__(self, pieces):
        self.pieces = pieces
        self.calls = 0

    def transcribe(self, source):
        self.calls += 1
        return list(self.pieces), Info()


SPOKEN = [Piece(0.0, 4.0, " Первая фраза "), Piece(4.0, 9.5, "Вторая фраза")]

# --- the documented names are the written names (№101) -----------------------

with tempfile.TemporaryDirectory() as raw:
    root = Path(raw)
    paths = transcribe.output_paths(root, "Встреча")
    note(set(paths) == {"transcript", "summary", "detailed"}, f"unexpected outputs: {list(paths)}")
    note(paths["transcript"].name == "Встреча - transcript.md", f"unexpected name: {paths['transcript'].name}")
    note(paths["transcript"].parent == root / "Transcript" / "Встреча",
         f"unexpected directory: {paths['transcript'].parent}")
    # The documentation of the skill promises exactly these names, and the
    # upstream script wrote different ones — so the promise is checked against
    # the code rather than against a second copy of the promise.
    skill = (SKILL / "SKILL.md").read_bytes().decode("utf-8")
    for pattern in transcribe.OUTPUTS.values():
        note(pattern.replace("{name}", "<имя>") in skill,
             f"the skill does not document the name it writes: {pattern}")

# --- an empty transcription is a failure, not an empty file (№104) -----------

with tempfile.TemporaryDirectory() as raw:
    source = Path(raw) / "запись.m4a"
    source.write_bytes(b"not really audio")

    try:
        transcribe.transcribe(source, backend=Engine([]))
        failures.append("a run without a single segment must not be a result")
    except transcribe.TranscribeError as error:
        note("сегмент" in str(error), f"the refusal must say what happened: {error}")

    try:
        transcribe.transcribe(Path(raw) / "нет.m4a", backend=Engine(SPOKEN))
        failures.append("a missing file must be refused")
    except transcribe.TranscribeError:
        pass

    result = transcribe.transcribe(source, backend=Engine(SPOKEN))
    note(len(result.segments) == 2 and result.language == "ru", f"a normal run must work: {result}")
    note(result.text == "Первая фраза\nВторая фраза", f"unexpected text: {result.text!r}")

    # Time that goes backwards means the model repeated itself, and a transcript
    # assembled from that quietly loses text.
    try:
        transcribe.transcribe(source, backend=Engine([Piece(10.0, 12.0, "поздняя"),
                                                      Piece(2.0, 3.0, "ранняя")]))
        failures.append("segments that go backwards must be refused")
    except transcribe.TranscribeError as error:
        note("таймкод" in str(error), f"the refusal must name the problem: {error}")

# --- rendering -------------------------------------------------------------

result = transcribe.Transcription(list(SPOKEN), "ru", "small")
markdown = transcribe.render(result, "Встреча")
note("**[00:00:00]**" in markdown and "**[00:00:04]**" in markdown,
     f"markdown must carry timestamps: {markdown}")
note("Распознавание выполнено локально" in markdown,
     "the result must say where the recognition happened")
plain = transcribe.render(result, "Встреча", "txt")
note(plain.strip() == "Первая фраза\nВторая фраза", f"unexpected plain text: {plain!r}")
document = json.loads(transcribe.render(result, "Встреча", "json"))
note([item["text"] for item in document["segments"]] == ["Первая фраза", "Вторая фраза"],
     f"unexpected json: {document}")
try:
    transcribe.render(result, "Встреча", "docx")
    failures.append("an unknown format must be refused")
except transcribe.TranscribeError:
    pass

# --- frame extraction is fail-closed (№104) ----------------------------------


class Runner:
    """An ffmpeg that exits with the code the test chose, writing what it says."""

    def __init__(self, code: int = 0, frames: int = 0, destination: Path | None = None):
        self.code, self.frames, self.destination = code, frames, destination
        self.commands: list[list[str]] = []

    def __call__(self, command, timeout):
        self.commands.append(command)
        if self.destination is not None:
            for number in range(self.frames):
                (self.destination / f"frame-{number:04d}.png").write_bytes(b"\x89PNG")
        return self.code, "ffmpeg output"


with tempfile.TemporaryDirectory() as raw:
    root = Path(raw)
    source = root / "демо.mp4"
    source.write_bytes(b"not really video")
    destination = root / "screenshots"

    # This is the defect verbatim: ffmpeg fails, writes nothing, and the caller
    # used to take the empty list for "a video with no frames".
    try:
        transcribe.extract_frames(source, destination, runner=Runner(code=1, destination=destination))
        failures.append("a failing ffmpeg must not look like a video without frames")
    except transcribe.TranscribeError as error:
        note("код" in str(error), f"the refusal must carry the exit code: {error}")

    # And the subtler half: exit code zero with nothing written.
    try:
        transcribe.extract_frames(source, destination, runner=Runner(code=0, destination=destination))
        failures.append("a successful command that wrote no frames must not pass")
    except transcribe.TranscribeError as error:
        note("не создал" in str(error), f"the refusal must say what is missing: {error}")

    runner = Runner(code=0, frames=3, destination=destination)
    frames = transcribe.extract_frames(source, destination, runner=runner)
    note(len(frames) == 3, f"the frames that were written must be returned: {frames}")
    note(runner.commands and runner.commands[0][0] == "ffmpeg", "frames come from ffmpeg")

# --- outputs appear together or not at all -----------------------------------

with tempfile.TemporaryDirectory() as raw:
    root = Path(raw)
    first, second = root / "Transcript/Имя/a.md", root / "Transcript/Имя/b.md"
    transcribe.write_atomically({first: "первый\n", second: "второй\n"})
    note(first.is_file() and second.is_file(), "both results must be written")
    note(not list(first.parent.glob("*.part")), "no staging file may survive a success")

    # A half-written set with the right names is indistinguishable from a
    # complete one, which is why the write is staged — and why a rename that
    # fails halfway undoes what has already landed.
    broken = root / "Transcript/Имя2/c.md"
    try:
        transcribe.write_atomically({broken: "текст\n", root: "каталог вместо файла\n"})
        failures.append("writing into a directory must fail")
    except OSError:
        pass
    note(not broken.exists(), "a failed set must leave nothing behind")
    note(not list((root / "Transcript/Имя2").glob("*.part")) if (root / "Transcript/Имя2").is_dir() else True,
         "no staging file may survive a failure")

# --- no media leaves the machine in the default flow (№102) ------------------

source_text = (SKILL / "scripts/transcribe.py").read_bytes().decode("utf-8")
# Code, not prose: the docstring is allowed to say that nothing is uploaded, and
# a check over the whole file would forbid explaining the very property it is
# checking. What must not appear is an import or a call.
code = "\n".join(line for line in source_text.splitlines() if not line.strip().startswith("#"))
for forbidden in ("import google", "from google", "genai", "gemini", "import requests",
                  "urlopen", "httpx", "urllib.request", ".upload("):
    note(forbidden not in code.lower(),
         f"the local transcription must not use '{forbidden}'")
note("faster_whisper" in source_text, "the local backend must be the one that is used")

# --- the dependency contract is named, not implied (№103) --------------------

try:
    transcribe.load_backend("small", "int8")
except transcribe.TranscribeError as error:
    note("faster-whisper" in str(error) and "разрешения" in str(error),
         f"a missing dependency must name itself and the rule for installing it: {error}")
except ImportError:
    failures.append("a missing dependency must be a TranscribeError, not an ImportError")

document = (ROOT / "templates/new-project/capabilities/transcribe/TRANSCRIBE.template.md")
# Collapsed: a wrapped line is the same sentence, and a check that cannot see
# past a line break would be satisfied by rewrapping rather than by wording.
body = " ".join(document.read_bytes().decode("utf-8").split())
for dependency in ("Python 3.9+", "faster-whisper", "FFmpeg", "модель Whisper"):
    note(dependency in body, f"the user documentation must name the dependency {dependency}")
note("conditional" in body, "the documentation must say which dependencies are conditional")
note("не загружается" in body, "the documentation must state that the media stays local")

if failures:
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    print(f"{len(failures)} transcribe check(s) failed.", file=sys.stderr)
    raise SystemExit(1)

print("Transcribe checks passed.")
