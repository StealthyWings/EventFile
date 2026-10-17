import io
import json

import pytest
from PIL import Image

from eventfile.vision import (
    AttendanceRow,
    EventDetails,
    Reader,
    SheetResult,
    parse_attendance_table,
    parse_json,
    summarise_attendance,
)


def fake_chat(*replies):
    """A stand-in for ollama.chat that returns the given replies in order."""
    calls = []

    def chat(**kwargs):
        reply = replies[len(calls)]
        calls.append(kwargs)
        return {"message": {"content": reply if isinstance(reply, str) else json.dumps(reply)}}

    chat.calls = calls
    return chat


@pytest.fixture
def image(tmp_path):
    p = tmp_path / "poster.jpg"
    Image.new("RGB", (3000, 2000), "white").save(p)
    return p


def test_parse_json_tolerates_code_fences():
    assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json('Here you go: {"a": 2} hope that helps') == {"a": 2}


def test_read_poster_transcribes_then_extracts(image):
    fields = {
        "title": "Workshop on Drone Mapping",
        "organiser": "Geography Club",
        "date": "2026-10-14",
        "time": "10:00 AM",
        "venue": "Seminar Hall 2",
        "resource_person": "Dr. A. Kumar",
        "resource_person_role": "Professor, IIT Madras",
        "event_type": "Workshop",
    }
    chat = fake_chat("WORKSHOP ON DRONE MAPPING\nDr. A. Kumar", fields)
    reader = Reader(chat=chat)
    details = reader.read_poster(image)

    assert details.title == "Workshop on Drone Mapping"
    assert details.event_date.isoformat() == "2026-10-14"
    assert reader.poster_text.startswith("WORKSHOP ON DRONE MAPPING")

    first, second = chat.calls
    with Image.open(io.BytesIO(first["messages"][0]["images"][0])) as im:
        assert max(im.size) <= 1600
    assert "format" not in first  # free transcription, no JSON constraint
    assert "images" not in second["messages"][0]
    assert "Dr. A. Kumar" in second["messages"][0]["content"]


def test_read_poster_bad_date_becomes_none(image):
    chat = fake_chat("text", {"title": "X", "date": "next Friday"})
    assert Reader(chat=chat).read_poster(image).event_date is None


TABLE = """Here is the table:

| S.No | Name | Reg. No | Signature |
|---|---|---|---|
| 1 | Priya S | 21CS001 | yes |
| 2. | Arun K |  | no |
|  | Unnumbered Person | 21IT9 | Yes |
| 4 |  | 21CS4 | no |
"""


def test_parse_attendance_table():
    rows = parse_attendance_table(TABLE)
    assert [r.name for r in rows] == ["Priya S", "Arun K", "Unnumbered Person"]
    assert [r.serial for r in rows] == [1, 2, None]
    assert [r.signed for r in rows] == [True, False, True]
    assert rows[1].register_number == ""


def test_read_attendance(image):
    sheet = Reader(chat=fake_chat(TABLE)).read_attendance(image)
    assert sheet.source == "poster.jpg" and len(sheet.rows) == 3


def rows(*serials):
    return [AttendanceRow(s, f"Student {s}", f"REG{s:03d}", True) for s in serials]


def test_summary_counts_and_no_warnings_when_consistent():
    s = summarise_attendance([SheetResult("p1.jpg", rows(1, 2, 3)), SheetResult("p2.jpg", rows(4, 5))])
    assert s.count == 5 and s.signed == 5 and s.warnings == []


def test_summary_flags_skipped_serials():
    s = summarise_attendance([SheetResult("p1.jpg", rows(1, 2, 5))])
    assert any("p1.jpg" in w and "3" in w for w in s.warnings)


def test_summary_flags_duplicates_and_unsigned():
    dup = rows(1, 2) + [AttendanceRow(3, "Student 1 again", "REG001", False)]
    s = summarise_attendance([SheetResult("p1.jpg", dup)])
    assert any("REG001" in w for w in s.warnings)
    assert any("signature" in w for w in s.warnings)
    assert s.count == 3 and s.signed == 2


def test_write_narrative_sends_notes_and_counts():
    chat = fake_chat({"objective": "o", "summary": "s", "outcome": "u"})
    out = Reader(chat=chat).write_narrative(
        EventDetails(title="Drone Mapping"), "நல்ல workshop, students flew drones", 42
    )
    assert out == {"objective": "o", "summary": "s", "outcome": "u"}
    prompt = chat.calls[0]["messages"][-1]["content"]
    assert "42" in prompt and "நல்ல workshop" in prompt
