from datetime import date, datetime

from PIL import Image

from eventfile.photos import caption, check_photo, read_photo_meta, stamp


def make_jpeg(path, taken="2026:10:14 10:42:05", lat=None, lon=None):
    img = Image.new("RGB", (640, 480), (90, 120, 160))
    exif = Image.Exif()
    if taken:
        exif.get_ifd(0x8769)[36867] = taken  # DateTimeOriginal
    if lat is not None:
        gps = exif.get_ifd(0x8825)
        gps[1] = "N" if lat >= 0 else "S"
        gps[2] = _dms(abs(lat))
        gps[3] = "E" if lon >= 0 else "W"
        gps[4] = _dms(abs(lon))
    img.save(path, exif=exif)
    return path


def _dms(value):
    d = int(value)
    m = int((value - d) * 60)
    s = round(((value - d) * 60 - m) * 60, 2)
    return (float(d), float(m), s)


def test_reads_date_and_gps(tmp_path):
    p = make_jpeg(tmp_path / "a.jpg", lat=13.0108, lon=80.2354)
    meta = read_photo_meta(p)
    assert meta.taken_at == datetime(2026, 10, 14, 10, 42, 5)
    assert abs(meta.lat - 13.0108) < 1e-4
    assert abs(meta.lon - 80.2354) < 1e-4


def test_southern_and_western_hemispheres_are_negative(tmp_path):
    p = make_jpeg(tmp_path / "b.jpg", lat=-33.8688, lon=-70.6693)
    meta = read_photo_meta(p)
    assert meta.lat < 0 and meta.lon < 0


def test_missing_exif_gives_none(tmp_path):
    p = tmp_path / "plain.png"
    Image.new("RGB", (10, 10)).save(p)
    meta = read_photo_meta(p)
    assert meta.taken_at is None and meta.lat is None and meta.lon is None


def test_caption_includes_label_date_and_coordinates(tmp_path):
    meta = read_photo_meta(make_jpeg(tmp_path / "c.jpg", lat=13.0108, lon=80.2354))
    text = caption(meta, "Inaugural address")
    assert text.startswith("Inaugural address")
    assert "14 Oct 2026" in text and "10:42" in text
    assert "13.0108° N" in text and "80.2354° E" in text


def test_check_flags_missing_gps_and_wrong_day(tmp_path):
    no_gps = read_photo_meta(make_jpeg(tmp_path / "d.jpg"))
    assert any("location" in w for w in check_photo(no_gps, date(2026, 10, 14)))

    other_day = read_photo_meta(
        make_jpeg(tmp_path / "e.jpg", taken="2026:09:01 09:00:00", lat=13.0, lon=80.0)
    )
    assert any("01 Sep 2026" in w for w in check_photo(other_day, date(2026, 10, 14)))

    good = read_photo_meta(make_jpeg(tmp_path / "f.jpg", lat=13.0, lon=80.0))
    assert check_photo(good, date(2026, 10, 14)) == []


def test_stamp_adds_a_strip_and_keeps_width(tmp_path):
    src = make_jpeg(tmp_path / "g.jpg", lat=13.0108, lon=80.2354)
    out = stamp(read_photo_meta(src), tmp_path / "g_stamped.jpg")
    with Image.open(out) as im:
        assert im.width == 640 and im.height > 480
