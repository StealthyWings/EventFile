"""Read date/time and GPS from photo EXIF, caption it, and stamp it on the image.

Everything here is deterministic: the model never writes a date or a coordinate.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

EXIF_IFD = 0x8769
GPS_IFD = 0x8825
DATETIME_ORIGINAL = 36867
DATETIME = 306
MAX_WIDTH = 1600


@dataclass
class PhotoMeta:
    path: Path
    taken_at: datetime | None
    lat: float | None
    lon: float | None

    @property
    def has_location(self) -> bool:
        return self.lat is not None and self.lon is not None


def read_photo_meta(path) -> PhotoMeta:
    path = Path(path)
    with Image.open(path) as im:
        exif = im.getexif()
        taken = _parse_exif_datetime(
            exif.get_ifd(EXIF_IFD).get(DATETIME_ORIGINAL) or exif.get(DATETIME)
        )
        lat, lon = _parse_gps(exif.get_ifd(GPS_IFD))
    return PhotoMeta(path, taken, lat, lon)


def _parse_exif_datetime(raw) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.strptime(str(raw).strip("\x00 "), "%Y:%m:%d %H:%M:%S")
    except ValueError:
        return None


def _parse_gps(gps) -> tuple[float | None, float | None]:
    try:
        lat = _dms_to_degrees(gps[2], gps[1])
        lon = _dms_to_degrees(gps[4], gps[3])
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return None, None
    return lat, lon


def _dms_to_degrees(dms, ref) -> float:
    d, m, s = (float(x) for x in dms)
    value = d + m / 60 + s / 3600
    return -value if str(ref).upper().startswith(("S", "W")) else value


def format_coords(meta: PhotoMeta) -> str:
    ns = "N" if meta.lat >= 0 else "S"
    ew = "E" if meta.lon >= 0 else "W"
    return f"{abs(meta.lat):.4f}° {ns}, {abs(meta.lon):.4f}° {ew}"


def format_when(meta: PhotoMeta) -> str:
    return meta.taken_at.strftime("%d %b %Y, %I:%M %p")


def caption(meta: PhotoMeta, label: str = "") -> str:
    parts = []
    if meta.taken_at:
        parts.append(format_when(meta))
    if meta.has_location:
        parts.append(format_coords(meta))
    details = " · ".join(parts) or "date and location not recorded in photo"
    return f"{label} — {details}" if label else details


def check_photo(meta: PhotoMeta, event_day: date | None) -> list[str]:
    """Problems an accreditation assessor would query."""
    name = meta.path.name
    problems = []
    if not meta.has_location:
        problems.append(f"{name}: no GPS location in the photo (turn on location in the camera app)")
    if meta.taken_at is None:
        problems.append(f"{name}: no date/time in the photo")
    elif event_day and meta.taken_at.date() != event_day:
        problems.append(
            f"{name}: taken on {meta.taken_at:%d %b %Y}, not on the event day "
            f"({event_day:%d %b %Y})"
        )
    return problems


def _font(size: int):
    for name in ("arial.ttf", "segoeui.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def stamp(meta: PhotoMeta, out_path, place: str = "") -> Path:
    """Copy the photo with a strip underneath showing date, time and coordinates."""
    out_path = Path(out_path)
    with Image.open(meta.path) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
    if im.width > MAX_WIDTH:
        im = im.resize((MAX_WIDTH, round(im.height * MAX_WIDTH / im.width)))

    lines = [place] if place else []
    lines.append(format_when(meta) if meta.taken_at else "Date/time not recorded")
    if meta.has_location:
        lines.append(f"Lat {meta.lat:.6f}  Long {meta.lon:.6f}")
    else:
        lines.append("Location not recorded")

    size = max(14, im.width // 40)
    font = _font(size)
    pad = size // 2
    strip_h = pad * 2 + len(lines) * (size + pad // 2)
    canvas = Image.new("RGB", (im.width, im.height + strip_h), (20, 20, 20))
    canvas.paste(im, (0, 0))
    draw = ImageDraw.Draw(canvas)
    y = im.height + pad
    for line in lines:
        draw.text((pad, y), line, fill=(255, 255, 255), font=font)
        y += size + pad // 2
    canvas.save(out_path, quality=88)
    return out_path
