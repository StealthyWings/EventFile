# EventFile

Turn a college club event's **poster**, **attendance sheet photos** and **phone photos** into the
event report an IQAC / NAAC accreditation file needs: event details, participant count,
objective / summary / outcome, geotagged photos with captions, signature block, and annexures.

Everything runs on your laptop. The poster and attendance sheets are read by **Gemma 4**
(open weights, Apache 2.0) through **Ollama**. Students' names, register numbers and photos never
leave the machine.

## Why

After every club event, someone has to build the "event file": copy last time's Word report,
retype the poster, count signatures, re-shoot or watermark photos with a GPS camera app, and caption
each one. Assessors send back queries when photos aren't geotagged or captioned properly.

The evidence is already on someone's phone: date, time and GPS sit in each photo's EXIF data, and the
title, date and speaker are printed on the poster. EventFile reads them and lays them out.

## Run it

Needs Python 3.10+ and [Ollama](https://ollama.com).

```bash
ollama pull gemma4:e4b-it-qat
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:7860, click **Load a sample event**, then **Read files with Gemma**.
If Ollama isn't already running, the app starts `ollama serve` in the background for you
(set `OLLAMA_EXE` if `ollama` isn't on your PATH).

Use a different model with `EVENTFILE_MODEL=gemma4:e2b-it-qat` (smaller, faster, weaker at handwriting).

## How it works

```
poster ──► Gemma: transcribe text ──► Gemma: pull fields from the text ─┐
attendance sheets ──► Gemma: markdown table ──► parsed in Python ───────┼─► you review & edit ─► .docx
photos ──► EXIF date/time + GPS (Python) ──► stamped strip + caption ───┤
your notes (Tamil / English) ──► Gemma: objective, summary, outcome ────┘
```

The rule: **the model reads and writes prose; code produces every number.**

- Participant count = rows in the attendance table (which you can edit), not a number the model states.
- Photo dates and coordinates come from EXIF. A photo with no GPS, or taken on a different day than the
  event, is flagged in the **Evidence check**.
- Serial-number gaps on a sheet (S.No 7 then 9) are flagged as a possibly skipped row. Duplicate register
  numbers and unsigned rows are flagged too.
- The narrative prompt passes only the facts from the poster, the count and your notes, and tells the
  model not to invent names, numbers or outcomes.

## What I measured (sample event, RTX 3050 4 GB laptop, `gemma4:e4b-it-qat`)

| Step | Result | Time |
|---|---|---|
| Poster, JSON straight from the image | 7/8 fields; speaker came back as "Dr. Meekshi" | ~12 s |
| Poster, transcribe then extract (what the app does) | **8/8 fields**, "Dr. R. Meenakshi" | ~22 s |
| Attendance, 22 handwritten rows over 2 sheets | 22/22 rows, 22/22 register numbers, 21/22 names exact ("Nandini" for "Nandhini") | ~22–27 s per sheet |
| Signature column | 19–20/22 correct across runs; it tends to call the last row on a sheet unsigned and missed one blank cell | (same call) |
| Photo captions | Short, plausible, editable | ~3 s per photo |
| Narrative from Tamil–English notes | Correct, formal English, no invented facts | ~17 s |
| **Whole sample event in the app** | poster + 2 sheets + 4 photos + narrative | **~95 s** |

Signatures are the weakest part, so the app says so and the review table lets you fix them before
exporting. The attendance sheet photos are always attached as an annexure, so the real signatures are
in the file either way.

## Project layout

```
app.py                 Gradio UI (read → review → build)
eventfile/photos.py    EXIF date/GPS, captions, stamped photos, evidence checks
eventfile/vision.py    Gemma 4 via Ollama: poster, attendance, photo captions, narrative
eventfile/report.py    Word report (python-docx)
eventfile/pipeline.py  Glue for the two steps
eventfile/theme.py     Dark slate + green look, offline fonts only
scripts/make_samples.py      Generates the fictional sample event in samples/
scripts/take_screenshots.py  Runs the sample through the app in Edge and saves screenshots
scripts/watch_connections.ps1  Logs any non-localhost connection from the app or Ollama
tests/                 pytest, no model needed (the model is faked)
```

Run the tests with `pytest`.

## Limitations

- One report layout. Colleges have their own templates; adapting to a department's template is next.
- Messy real-world sheets (carbon copies, folded paper, very poor light) haven't been tested yet.
- Photos must be the original files. Images forwarded through WhatsApp lose their EXIF data, so
  they'll show up as "no GPS" in the Evidence check.

## License

MIT for this code (see [LICENSE](LICENSE)). Gemma 4 is released by Google under Apache 2.0.
