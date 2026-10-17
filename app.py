"""EventFile web app.  Run:  python app.py   then open http://127.0.0.1:7860"""

from __future__ import annotations

import os
import runpy
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")  # no usage pings: the app stays offline

import gradio as gr

from eventfile.photos import format_coords, format_when
from eventfile.pipeline import make_report, read_event
from eventfile.theme import CSS, THEME
from eventfile.vision import MODEL, AttendanceRow, EventDetails, ensure_ollama_running, model_problem

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "output"
SAMPLES = ROOT / "samples"

SAMPLE_NOTES = (
    "நல்ல response. Students ollama install pannitu Gemma run panninaanga. "
    "3 teams built a small chatbot in the hands-on session. "
    "Next time longer session venum nu sonnanga."
)

LOGO = """<svg viewBox="0 0 22 26" aria-hidden="true">
  <path d="M2 1h12l6 6v18H2z" fill="none" stroke="#00ED64" stroke-width="2" stroke-linejoin="round"/>
  <path d="M14 1v6h6" fill="none" stroke="#00ED64" stroke-width="2" stroke-linejoin="round"/>
  <path d="M6 15.5l3 3 7-7" fill="none" stroke="#FFFFFF" stroke-width="2.2" stroke-linecap="round"/>
</svg>"""

HERO = f"""
<div class="ef-nav">
  <div class="ef-brand">{LOGO}EventFile</div>
  <div class="ef-nav-meta">
    <span>For college clubs</span><span>IQAC · NAAC</span>
    <span class="ef-pill"><span class="ef-dot"></span>&nbsp; OFFLINE · GEMMA 4</span>
  </div>
</div>
<div class="ef-hero">
  <h1>Poster. Sheets. Photos.<br>One report.</h1>
  <p>Turn a club event's poster, attendance sheets and phone photos into the event report your
  IQAC/NAAC file needs. Read by Gemma 4 (<code>{MODEL}</code>) through Ollama, so students' names
  and register numbers never leave this machine.</p>
</div>
"""


def step_header(number: str, title: str, blurb: str, dot: str = "") -> str:
    return (
        f'<div class="ef-step"><div class="ef-eyebrow"><span class="ef-dot {dot}"></span>Step {number}</div>'
        f"<h2>{title}</h2><p>{blurb}</p></div>"
    )


def _paths(files) -> list[Path]:
    return [Path(f if isinstance(f, str) else f.name) for f in (files or [])]


def _truthy(value) -> bool:
    return value is True or str(value).strip().lower() in {"true", "yes", "1", "✓"}


def _int(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def warnings_markdown(warnings: list[str]) -> str:
    if not warnings:
        return "### Evidence check\nNothing an assessor is likely to query."
    return "### Evidence check\n" + "\n".join(f"- {w}" for w in warnings)


def timings_markdown(timings) -> str:
    groups = defaultdict(lambda: [0, 0.0])
    for task, seconds in timings:
        key = task.split(":")[0]
        groups[key][0] += 1
        groups[key][1] += seconds
    parts = [f"{key} ×{n}: {sec:.0f} s" if n > 1 else f"{key}: {sec:.0f} s" for key, (n, sec) in groups.items()]
    total = sum(sec for _, sec in timings)
    return (f"Gemma 4 on this laptop: {' · '.join(parts)} — total {total:.0f} s. "
            "No internet calls were made.")


def load_samples():
    if not (SAMPLES / "poster.jpg").exists():
        runpy.run_path(str(ROOT / "scripts" / "make_samples.py"), run_name="__main__")
    return (
        "Sample College of Engineering, Chennai",
        str(SAMPLES / "poster.jpg"),
        [str(p) for p in sorted(SAMPLES.glob("attendance_*.jpg"))],
        [str(p) for p in sorted(SAMPLES.glob("photo_*.jpg"))],
        SAMPLE_NOTES,
    )


def on_read(poster, sheets, photos, notes, describe, progress=gr.Progress()):
    problem = model_problem()
    if problem:
        raise gr.Error(problem)
    sheets, photos = _paths(sheets), _paths(photos)
    if not (poster or sheets or photos):
        raise gr.Error("Add at least a poster, an attendance sheet or a photo.")

    result = read_event(
        poster, sheets, photos, notes or "", describe,
        progress=lambda fraction, message: progress(fraction, desc=message),
    )
    d = result.details
    attendance = [[r.serial, r.name, r.register_number, r.signed] for r in result.rows]
    photo_rows = [
        [
            m.path.name,
            label,
            format_when(m) if m.taken_at else "missing",
            format_coords(m) if m.has_location else "missing",
        ]
        for m, label in result.photos
    ]
    state = {"poster": poster, "sheets": [str(s) for s in sheets], "photos": [str(m.path) for m, _ in result.photos]}
    n = result.narrative
    return (
        d.title, d.event_type, d.organiser, d.date, d.time, d.venue, d.resource_person, d.resource_person_role,
        attendance, photo_rows, n["objective"], n["summary"], n["outcome"],
        warnings_markdown(result.warnings), timings_markdown(result.timings), state,
        gr.update(interactive=True),
    )


def on_build(institution, title, event_type, organiser, date, time, venue, person, role,
             attendance, photo_rows, objective, summary, outcome, include_names, state):
    if not state:
        raise gr.Error("Read the files first.")
    details = EventDetails(title, organiser, date, time, venue, person, role, event_type)
    rows = [
        AttendanceRow(_int(r[0]), str(r[1] or "").strip(), str(r[2] or "").strip(), _truthy(r[3]))
        for r in (attendance or [])
        if len(r) >= 4 and str(r[1] or "").strip()
    ]
    photos = [(Path(p), str(row[1] or "")) for p, row in zip(state["photos"], photo_rows or [])]
    path, warnings = make_report(
        details, rows, photos,
        {"objective": objective, "summary": summary, "outcome": outcome},
        OUT_DIR, institution, state.get("poster"), state.get("sheets", []), include_names,
    )
    signed = sum(r.signed for r in rows)
    summary_line = f"**Report ready:** {len(rows)} participants ({signed} signed), {len(photos)} photos stamped with date, time and location."
    return str(path), summary_line + "\n\n" + warnings_markdown(warnings)


ensure_ollama_running()

with gr.Blocks(title="EventFile", analytics_enabled=False) as demo:
    gr.HTML(HERO)
    problem = model_problem()
    if problem:
        gr.Markdown(f"**Gemma isn't ready.** {problem}", elem_classes=["ef-banner"])
    state = gr.State({})

    with gr.Row(equal_height=False):
        with gr.Column(scale=2, min_width=320, elem_classes=["ef-card"]):
            gr.HTML(step_header("01", "Add the event's files",
                                "The poster, attendance sheets and the original photos from the phone."))
            sample_btn = gr.Button("Load a sample event  ›", size="sm", elem_classes=["ef-link"])
            institution = gr.Textbox(label="College name", placeholder="e.g. Sample College of Engineering, Chennai")
            poster = gr.Image(label="Poster / brochure", type="filepath", height=280, elem_classes=["ef-upload"])
            sheets = gr.File(label="Attendance sheet photos", file_count="multiple", file_types=["image"],
                             elem_classes=["ef-upload"])
            photos = gr.File(
                label="Event photos (originals, so GPS is kept)",
                file_count="multiple", file_types=["image"], elem_classes=["ef-upload"],
            )
            notes = gr.Textbox(label="What happened? A few lines in Tamil, English or both", lines=4)
            describe = gr.Checkbox(label="Let Gemma suggest a caption for each photo (a few seconds each)", value=True)
            read_btn = gr.Button("Read files with Gemma", variant="primary", size="lg")

        with gr.Column(scale=3, min_width=360):
            with gr.Column(elem_classes=["ef-card"]):
                gr.HTML(step_header("02", "Check what Gemma read",
                                    "Fix anything that's wrong. Counts, dates and GPS come from the files, "
                                    "not from the model.", dot="purple"))
                warnings_md = gr.Markdown(min_height=60, elem_classes=["ef-evidence"])
                with gr.Row():
                    title = gr.Textbox(label="Event title", scale=3)
                    event_type = gr.Textbox(label="Type", scale=1)
                organiser = gr.Textbox(label="Organised by")
                with gr.Row():
                    date = gr.Textbox(label="Date (YYYY-MM-DD)")
                    time = gr.Textbox(label="Time")
                    venue = gr.Textbox(label="Venue")
                with gr.Row():
                    person = gr.Textbox(label="Resource person")
                    role = gr.Textbox(label="Designation and institution")
                attendance = gr.Dataframe(
                    label="Attendance (count = rows with a name)",
                    headers=["S.No", "Name", "Reg. No", "Signed"],
                    datatype=["number", "str", "str", "bool"],
                    type="array", interactive=True, wrap=True,
                )
                photo_table = gr.Dataframe(
                    label="Photos (edit the caption; date and location come from the photo itself)",
                    headers=["Photo", "Caption", "Taken", "Location"],
                    datatype=["str", "str", "str", "str"],
                    static_columns=[0, 2, 3], type="array", interactive=True, wrap=True,
                    column_widths=["17%", "37%", "22%", "24%"],
                )
                objective = gr.Textbox(label="Objective", lines=2)
                summary = gr.Textbox(label="Summary of the event", lines=5)
                outcome = gr.Textbox(label="Outcome", lines=2)

            with gr.Column(elem_classes=["ef-card"]):
                gr.HTML(step_header("03", "Build the report",
                                    "A Word file with the details table, stamped photos, signature block "
                                    "and annexures.", dot="blue"))
                include_names = gr.Checkbox(label="Add a typed list of participants as an annexure", value=False)
                build_btn = gr.Button("Build the report", variant="primary", size="lg", interactive=False)
                report_file = gr.File(label="Event report (.docx)")
                final_md = gr.Markdown(elem_classes=["ef-evidence"])
                timing_md = gr.Markdown(elem_classes=["ef-timing"])

    sample_btn.click(load_samples, outputs=[institution, poster, sheets, photos, notes])
    read_btn.click(
        on_read,
        inputs=[poster, sheets, photos, notes, describe],
        outputs=[title, event_type, organiser, date, time, venue, person, role, attendance, photo_table,
                 objective, summary, outcome, warnings_md, timing_md, state, build_btn],
        show_progress_on=[warnings_md],
    )
    build_btn.click(
        on_build,
        inputs=[institution, title, event_type, organiser, date, time, venue, person, role,
                attendance, photo_table, objective, summary, outcome, include_names, state],
        outputs=[report_file, final_md],
    )


if __name__ == "__main__":
    OUT_DIR.mkdir(exist_ok=True)
    demo.launch(
        server_name="127.0.0.1",
        theme=THEME,
        css=CSS,
        allowed_paths=[str(OUT_DIR), str(SAMPLES)],
    )
