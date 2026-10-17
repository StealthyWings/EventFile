"""Read posters and attendance sheets with Gemma 4 running locally through Ollama.

The model reads and writes prose. It never decides a count, a date stamp or a
coordinate: counts come from the rows it lists, and the cross-checks below flag
anything that doesn't add up so a person can fix it before export.
"""

from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from PIL import Image, ImageOps

MODEL = os.environ.get("EVENTFILE_MODEL", "gemma4:e4b-it-qat")
MAX_SIDE = 1600

POSTER_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "organiser": {"type": "string"},
        "date": {"type": "string", "description": "YYYY-MM-DD, or empty"},
        "time": {"type": "string"},
        "venue": {"type": "string"},
        "resource_person": {"type": "string"},
        "resource_person_role": {"type": "string"},
        "event_type": {"type": "string"},
    },
    "required": ["title", "organiser", "date", "time", "venue", "resource_person",
                 "resource_person_role", "event_type"],
}

# Asking for strict JSON straight from the image made Gemma misread names
# ("Dr. R. Meenakshi" came back as "Dr. Meekshi"). Plain transcription reads them
# correctly, so images are transcribed first and structure is extracted afterwards.
TRANSCRIBE_POSTER = "Transcribe all the text on this poster exactly, line by line."

POSTER_FIELDS_PROMPT = """Below is the text of a poster for an event at an Indian college.
Fill in the event details using only this text. Use an empty string for anything that is not
in the text; do not guess. Give the date as YYYY-MM-DD.
organiser = the club, association or department hosting it (e.g. "Coding Club, Department of CSE").
resource_person = the chief guest or speaker; resource_person_role = their designation and institution.
event_type = one or two words such as Workshop, Seminar, Guest Lecture, Competition, Webinar.

Poster text:
"""

ATTENDANCE_PROMPT = """Transcribe this attendance sheet as a markdown table with the columns: S.No | Name | Reg. No | Signature.
Include only rows that have a name written in them. Copy names and numbers exactly as written.
In the Signature column write "yes" if that row's signature cell has any pen mark, or "no" if it is blank."""

DESCRIBE_PHOTO = """This photo is from a college event. Write a caption of at most 8 words saying
what is happening (e.g. "Resource person addressing the students"). Reply with the caption only."""

NARRATIVE_SCHEMA = {
    "type": "object",
    "properties": {
        "objective": {"type": "string"},
        "summary": {"type": "string"},
        "outcome": {"type": "string"},
    },
    "required": ["objective", "summary", "outcome"],
}


@dataclass
class EventDetails:
    title: str = ""
    organiser: str = ""
    date: str = ""
    time: str = ""
    venue: str = ""
    resource_person: str = ""
    resource_person_role: str = ""
    event_type: str = ""

    @property
    def event_date(self) -> date | None:
        try:
            return date.fromisoformat(self.date.strip())
        except ValueError:
            return None


@dataclass
class AttendanceRow:
    serial: int | None
    name: str
    register_number: str
    signed: bool


@dataclass
class SheetResult:
    source: str
    rows: list[AttendanceRow]


@dataclass
class AttendanceSummary:
    count: int
    signed: int
    warnings: list[str] = field(default_factory=list)


def parse_attendance_table(text: str) -> list[AttendanceRow]:
    """Turn the model's markdown table into rows. Header and separator lines are skipped."""
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 4 or set("".join(cells)) <= set("-: "):
            continue
        serial_text, name, reg, sig = cells[0], cells[1], cells[2], cells[-1]
        if name.lower() == "name" or not name:
            continue
        digits = re.search(r"\d+", serial_text)
        rows.append(
            AttendanceRow(
                serial=int(digits.group()) if digits else None,
                name=name,
                register_number=reg,
                signed=sig.lower().startswith(("y", "✓", "true")),
            )
        )
    return rows


def parse_json(text: str) -> dict:
    """Parse a model reply that should be JSON but may be wrapped in prose or fences."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _image_bytes(path) -> bytes:
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
    im.thumbnail((MAX_SIDE, MAX_SIDE))
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def _ollama_chat(**kwargs):
    import ollama

    return ollama.chat(**kwargs)


def _saved_user_env(name: str) -> str | None:
    """A Windows user environment variable as saved now, even if this terminal predates the change."""
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            return os.path.expandvars(winreg.QueryValueEx(key, name)[0])
    except (ImportError, OSError):
        return None


def _ollama_exe() -> str | None:
    candidates = [
        os.environ.get("OLLAMA_EXE"),
        shutil.which("ollama"),
        shutil.which("ollama", path=_saved_user_env("Path")),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe"),
    ]
    return next((c for c in candidates if c and Path(c).is_file()), None)


def ensure_ollama_running(wait_seconds: float = 30) -> bool:
    """Start `ollama serve` in the background if nothing is answering on its port."""
    import ollama

    def up() -> bool:
        try:
            ollama.list()
            return True
        except Exception:
            return False

    if up():
        return True
    exe = _ollama_exe()
    if not exe:
        return False
    env = os.environ.copy()
    models_dir = env.get("OLLAMA_MODELS") or _saved_user_env("OLLAMA_MODELS")
    if models_dir:
        env["OLLAMA_MODELS"] = models_dir
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.Popen([exe, "serve"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     creationflags=flags)
    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        time.sleep(1)
        if up():
            return True
    return False


def model_problem(model: str = MODEL) -> str | None:
    """Return a human-readable problem if Ollama or the model isn't ready, else None."""
    import ollama

    try:
        ollama.show(model)
    except ollama.ResponseError:
        return f"Model `{model}` isn't downloaded. Run: `ollama pull {model}`"
    except Exception:
        return "Can't reach Ollama on this laptop. Start the Ollama app, then reload this page."
    return None


class Reader:
    def __init__(self, chat=None, model: str = MODEL):
        self.chat = chat or _ollama_chat
        self.model = model
        self.timings: list[tuple[str, float]] = []
        self.poster_text = ""

    def _call(self, task: str, prompt: str, images=None, schema: dict | None = None) -> str:
        message = {"role": "user", "content": prompt}
        if images:
            message["images"] = [_image_bytes(p) for p in images]
        kwargs = dict(model=self.model, messages=[message], think=False, options={"temperature": 0})
        if schema:
            kwargs["format"] = schema
        start = time.perf_counter()
        reply = self.chat(**kwargs)
        self.timings.append((task, time.perf_counter() - start))
        return reply["message"]["content"]

    def read_poster(self, path) -> EventDetails:
        """Transcribe the poster, then pull fields out of the transcript (text only)."""
        self.poster_text = self._call("poster: transcribe", TRANSCRIBE_POSTER, images=[path]).strip()
        data = parse_json(
            self._call("poster: fields", POSTER_FIELDS_PROMPT + self.poster_text, schema=POSTER_SCHEMA)
        )
        known = EventDetails.__dataclass_fields__
        return EventDetails(**{k: str(v or "").strip() for k, v in data.items() if k in known})

    def read_attendance(self, path) -> SheetResult:
        text = self._call(f"attendance: {Path(path).name}", ATTENDANCE_PROMPT, images=[path])
        return SheetResult(Path(path).name, parse_attendance_table(text))

    def describe_photo(self, path) -> str:
        text = self._call(f"photo: {Path(path).name}", DESCRIBE_PHOTO, images=[path])
        return text.strip().strip('"').rstrip(".").splitlines()[0][:80] if text.strip() else ""

    def write_narrative(self, details: EventDetails, notes: str, participants: int) -> dict:
        prompt = f"""Write three short paragraphs for a college event report, in formal English.
Use only the facts below. Do not invent names, numbers, quotes or outcomes that are not given.
The coordinator's notes may be in Tamil, English or a mix; translate as needed.

Event: {details.title}
Type: {details.event_type}
Organised by: {details.organiser}
Date and time: {details.date} {details.time}
Venue: {details.venue}
Resource person: {details.resource_person}, {details.resource_person_role}
Participants (from the attendance sheets): {participants}

Coordinator's notes:
{notes.strip() or "(none)"}

objective: 1-2 sentences on why the event was held.
summary: 3-5 sentences on what happened.
outcome: 1-3 sentences on what participants gained."""
        data = parse_json(self._call("narrative", prompt, schema=NARRATIVE_SCHEMA))
        return {k: str(data.get(k, "")).strip() for k in ("objective", "summary", "outcome")}


def summarise_attendance(sheets: list[SheetResult], check_serials: bool = True) -> AttendanceSummary:
    warnings = []
    all_rows = [r for s in sheets for r in s.rows]

    for sheet in sheets if check_serials else []:
        serials = sorted({r.serial for r in sheet.rows if r.serial is not None})
        if serials:
            missing = sorted(set(range(serials[0], serials[-1] + 1)) - set(serials))
            if missing:
                listed = ", ".join(map(str, missing[:10]))
                warnings.append(
                    f"{sheet.source}: S.No {listed} not found. A row may have been skipped; "
                    "check the sheet."
                )

    regs = Counter(r.register_number.upper() for r in all_rows if r.register_number)
    for reg, n in sorted(regs.items()):
        if n > 1:
            warnings.append(f"Register number {reg} appears {n} times.")

    unsigned = [r.name for r in all_rows if not r.signed]
    if unsigned:
        names = ", ".join(unsigned[:8]) + ("…" if len(unsigned) > 8 else "")
        warnings.append(f"{len(unsigned)} row(s) without a signature: {names}")

    return AttendanceSummary(len(all_rows), len(all_rows) - len(unsigned), warnings)
