from docx import Document

from eventfile.pipeline import SIGNATURE_NOTE, make_report, read_event
from eventfile.vision import AttendanceRow, EventDetails, SheetResult
from tests.test_photos import make_jpeg


class FakeReader:
    timings = []

    def read_poster(self, path):
        return EventDetails(title="Robotics Expo", date="2026-10-14", venue="Main Hall")

    def read_attendance(self, path):
        start = 1 if "a1" in str(path) else 23
        return SheetResult(path.name, [AttendanceRow(start + i, f"S{start + i}", "", True) for i in range(3)])

    def describe_photo(self, path):
        return "Students at the robot stalls"

    def write_narrative(self, details, notes, participants):
        return {"objective": "o", "summary": f"{participants} attended", "outcome": "u"}


def test_read_event_combines_everything(tmp_path):
    good = make_jpeg(tmp_path / "good.jpg", lat=13.0, lon=80.0)
    no_gps = make_jpeg(tmp_path / "nogps.jpg")
    seen = []
    result = read_event(
        poster=tmp_path / "poster.jpg",
        sheets=[tmp_path / "a1.jpg", tmp_path / "a2.jpg"],
        photos=[good, no_gps],
        reader=FakeReader(),
        progress=lambda f, m: seen.append(m),
    )
    assert len(result.rows) == 6
    assert result.narrative["summary"] == "6 attended"
    assert [label for _, label in result.photos] == ["Students at the robot stalls"] * 2
    assert any("nogps.jpg" in w and "GPS" in w for w in result.warnings)
    assert SIGNATURE_NOTE in result.warnings
    # serials restart per sheet (1-3, 23-25): no false "row skipped" warning
    assert not any("S.No" in w for w in result.warnings)
    assert seen[0] == "Reading the poster"


def test_make_report_writes_docx_with_stamped_photos(tmp_path):
    photo = make_jpeg(tmp_path / "p.jpg", lat=13.0108, lon=80.2354)
    rows = [AttendanceRow(1, "Priya S", "21CS001", True), AttendanceRow(23, "Arun K", "", True),
            AttendanceRow(None, "  ", "", False)]
    path, warnings = make_report(
        EventDetails(title="Robotics Expo", date="2026-10-14", venue="Main Hall"),
        rows,
        [(photo, "Robot demo")],
        {"objective": "o", "summary": "s", "outcome": "u"},
        out_dir=tmp_path / "out",
    )
    assert path.exists() and path.suffix == ".docx"
    assert (path.parent / "photo_1.jpg").exists()
    doc = Document(path)
    text = "\n".join(p.text for p in doc.paragraphs) + "\n".join(
        c.text for t in doc.tables for r in t.rows for c in r.cells
    )
    assert "Robot demo — 14 Oct 2026" in text
    assert "Number of Participants\n2" in text or "\n2\n" in text
    assert warnings == []
