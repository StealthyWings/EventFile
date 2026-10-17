"""Run the sample event through the app and save screenshots for the write-up.

Needs the app running (python app.py) and:  pip install playwright mammoth
Drives the Microsoft Edge that ships with Windows, so no browser download.

Run:  python scripts/take_screenshots.py      (writes to screenshots/)
"""

import re
import shutil
from pathlib import Path

import mammoth
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "screenshots"
URL = "http://127.0.0.1:7860"
SCALE = 2  # retina-sharp images
GEMMA_TIMEOUT = 15 * 60 * 1000

REPORT_CSS = """
body { margin: 0; background: #E8EDEB; }
.page { width: 794px; margin: 0 auto; background: #fff; padding: 64px 72px; box-sizing: border-box;
        font-family: Calibri, "Segoe UI", sans-serif; font-size: 14.5px; color: #111; line-height: 1.45; }
.page > p:nth-of-type(-n+3) { text-align: center; }
table { border-collapse: collapse; width: 100%; margin: 12px 0; }
td { border: 1px solid #888; padding: 6px 10px; vertical-align: top; }
td:first-child { width: 34%; }
img { display: block; max-width: 82%; margin: 10px auto 4px; }
strong { color: #123456; }
"""


def saved(path: Path) -> Path:
    print("saved", path.relative_to(ROOT))
    return path


def settle(page, ms=1500):
    """Move the mouse off any button so no hover colours end up in a screenshot."""
    page.mouse.move(2, 2)
    page.wait_for_timeout(ms)


def crop(path: Path, out: Path, top_css: float, bottom_css: float) -> Path:
    with Image.open(path) as im:
        im.crop((0, int(top_css * SCALE), im.width, min(im.height, int(bottom_css * SCALE)))).save(out)
    return saved(out)


def render_report(browser, docx: Path):
    with docx.open("rb") as f:
        html = mammoth.convert_to_html(f).value
    page = browser.new_page(viewport={"width": 900, "height": 1200}, device_scale_factor=SCALE)
    page.set_content(f"<style>{REPORT_CSS}</style><div class='page'>{html}</div>")
    page.wait_for_load_state("load")
    sheet = page.locator(".page")
    full = saved(OUT / "08-report-full.png")
    sheet.screenshot(path=full)
    # first "page": header, details table, objective/summary/outcome and the first photo
    second_photo = page.locator(".page img").nth(1).bounding_box()
    top = sheet.bounding_box()["y"]
    crop(full, OUT / "07-report-page1.png", 0, second_photo["y"] - top - 8)
    page.close()


def main():
    OUT.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge")
        page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=SCALE,
                                color_scheme="dark")
        page.goto(URL)
        sample = page.get_by_role("button", name=re.compile("Load a sample event"))
        sample.wait_for()
        page.wait_for_timeout(1500)
        page.screenshot(path=saved(OUT / "01-landing.png"))

        cards = page.locator(".ef-card")
        step1, step2, step3 = cards.nth(0), cards.nth(1), cards.nth(2)

        sample.click()
        page.get_by_text("photo_4").first.wait_for()
        settle(page, 2000)
        step1.screenshot(path=saved(OUT / "02-step1-files.png"))

        page.get_by_role("button", name="Read files with Gemma").click()
        page.get_by_text(re.compile("Reading attendance sheet")).first.wait_for(timeout=GEMMA_TIMEOUT)
        settle(page, 4000)
        reading = OUT / "_reading_full.png"
        step2.screenshot(path=reading)
        crop(reading, OUT / "03-gemma-reading.png", 0, 300)
        reading.unlink()

        page.locator(".ef-evidence h3").first.wait_for(timeout=GEMMA_TIMEOUT)
        settle(page, 2500)
        review = saved(OUT / "04-step2-review-full.png")
        step2.screenshot(path=review)
        card_top = step2.bounding_box()["y"]
        photos_top = page.get_by_text("Photos (edit the caption").first.bounding_box()["y"] - card_top
        crop(review, OUT / "05a-review-details-attendance.png", 0, photos_top - 10)
        crop(review, OUT / "05b-review-photos-narrative.png", photos_top - 10, step2.bounding_box()["height"])

        page.get_by_role("button", name="Build the report", exact=True).click()
        page.get_by_text("Report ready").first.wait_for(timeout=120_000)
        settle(page)
        step3.screenshot(path=saved(OUT / "06-step3-report-ready.png"))
        page.screenshot(path=saved(OUT / "00-full-page.png"), full_page=True)

        docx = max((ROOT / "output").rglob("*.docx"), key=lambda f: f.stat().st_mtime)
        render_report(browser, docx)
        browser.close()

    stamped = sorted(docx.parent.glob("photo_*.jpg"))[0]
    shutil.copy(stamped, saved(OUT / "09-stamped-photo.jpg"))
    shutil.copy(ROOT / "samples" / "attendance_1.jpg", saved(OUT / "10-input-attendance-sheet.jpg"))


if __name__ == "__main__":
    main()
