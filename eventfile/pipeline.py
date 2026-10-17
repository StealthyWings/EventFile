"""The two steps the app runs: read the files with Gemma, then build the report."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .photos import PhotoMeta, caption, check_photo, read_photo_meta, stamp
from .report import PhotoEvidence, ReportData, build_report
from .vision import AttendanceRow, EventDetails, Reader, SheetResult, summarise_attendance

SIGNATURE_NOTE = (
    "Signatures are Gemma's guess and were wrong on 2–3 of 22 rows in testing. "
    "Tick them against the sheet before exporting."
)


@dataclass
class ReadResult:
    details: EventDetails
    rows: list[AttendanceRow]
    photos: list[tuple[PhotoMeta, str]]  # (metadata, label)
    narrative: dict
    warnings: list[str]
    timings: list[tuple[str, float]]


def evidence_warnings(details: EventDetails, sheets: list[SheetResult], photos: list[PhotoMeta],
                      check_serials: bool = True) -> list[str]:
    warnings = list(summarise_attendance(sheets, check_serials).warnings) if sheets else ["No attendance sheet added."]
    for meta in photos:
        warnings.extend(check_photo(meta, details.event_date))
    if not photos:
        warnings.append("No photos added. Assessors expect geotagged photos for every event.")
    if not details.event_date:
        warnings.append("Couldn't read the event date from the poster. Fill it in as YYYY-MM-DD.")
    return warnings


def read_event(poster, sheets, photos, notes="", describe_photos=True, reader=None,
               progress=lambda fraction, message: None) -> ReadResult:
    reader = reader or Reader()
    steps = (1 if poster else 0) + len(sheets) + (len(photos) if describe_photos else 0) + 1
    done = 0

    def tick(message):
        nonlocal done
        progress(done / steps, message)
        done += 1

    details = EventDetails()
    if poster:
        tick("Reading the poster")
        details = reader.read_poster(poster)

    sheet_results = []
    for path in sheets:
        tick(f"Reading attendance sheet {Path(path).name}")
        sheet_results.append(reader.read_attendance(path))
    rows = [r for s in sheet_results for r in s.rows]

    metas = [read_photo_meta(p) for p in photos]
    labelled = []
    for meta in metas:
        label = ""
        if describe_photos:
            tick(f"Captioning {meta.path.name}")
            label = reader.describe_photo(meta.path)
        labelled.append((meta, label))

    tick("Drafting objective, summary and outcome")
    narrative = reader.write_narrative(details, notes, len(rows))

    warnings = evidence_warnings(details, sheet_results, metas)
    if rows:
        warnings.append(SIGNATURE_NOTE)
    return ReadResult(details, rows, labelled, narrative, warnings, reader.timings)


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "event"


def make_report(details: EventDetails, rows: list[AttendanceRow], photos: list[tuple[Path, str]],
                narrative: dict, out_dir, institution: str = "", poster=None, sheets=(),
                include_names: bool = False) -> tuple[Path, list[str]]:
    """photos: (original path, label). Returns the .docx path and the final evidence check."""
    out_dir = Path(out_dir) / f"{details.date or 'undated'}-{slug(details.title)}"
    out_dir.mkdir(parents=True, exist_ok=True)

    evidence, metas = [], []
    for i, (path, label) in enumerate(photos, 1):
        meta = read_photo_meta(path)
        metas.append(meta)
        stamped = stamp(meta, out_dir / f"photo_{i}.jpg", place=details.venue)
        evidence.append(PhotoEvidence(stamped, caption(meta, label.strip())))

    rows = [r for r in rows if r.name.strip()]
    data = ReportData(
        details=details,
        participants=len(rows),
        objective=narrative.get("objective", ""),
        summary=narrative.get("summary", ""),
        outcome=narrative.get("outcome", ""),
        photos=evidence,
        institution=institution,
        poster=Path(poster) if poster else None,
        attendance_sheets=[Path(s) for s in sheets],
        attendees=rows if include_names else [],
    )
    path = build_report(data, out_dir / f"{slug(details.title)}-report.docx")
    # The edited table merges all sheets, so serial gaps between sheets aren't errors here.
    sheets_check = [SheetResult("attendance", rows)] if rows else []
    return path, evidence_warnings(details, sheets_check, metas, check_serials=False)
