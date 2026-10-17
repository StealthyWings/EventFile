"""Generate a fake event's poster, attendance sheets and photos for demos and tests.

Run:  python scripts/make_samples.py   (writes to samples/)
Everything here is fictional.
"""

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path(__file__).resolve().parent.parent / "samples"
FONTS = Path("C:/Windows/Fonts")
HANDS = ["Inkfree.ttf", "segoesc.ttf", "BRADHITC.TTF", "segoepr.ttf"]
random.seed(7)

NAMES = [
    ("Priya S", "21CS001"), ("Arun Kumar R", "21CS004"), ("Divya M", "21CS009"),
    ("Karthik V", "21CS012"), ("Sneha P", "21CS015"), ("Harish N", "21CS018"),
    ("Lakshmi K", "21CS021"), ("Vignesh S", "21CS023"), ("Nandhini R", "21CS027"),
    ("Sanjay M", "21CS030"), ("Keerthana B", "21IT002"), ("Pradeep J", "21IT006"),
    ("Swetha L", "21IT011"), ("Gokul A", "21IT014"), ("Aishwarya T", "22CS003"),
    ("Manoj D", "22CS007"), ("Kavya S", "22CS010"), ("Rahul P", "22CS016"),
    ("Deepika N", "22IT001"), ("Surya K", "22IT005"), ("Janani V", "22IT008"),
    ("Bharath R", "22IT013"),
]


def font(name, size):
    try:
        return ImageFont.truetype(str(FONTS / name), size)
    except OSError:
        return ImageFont.load_default(size)


def centered(draw, y, text, f, fill, width):
    w = draw.textlength(text, font=f)
    draw.text(((width - w) / 2, y), text, font=f, fill=fill)


def poster():
    W, H = 1200, 1700
    im = Image.new("RGB", (W, H), (250, 246, 238))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 300], fill=(18, 52, 86))
    centered(d, 50, "SAMPLE COLLEGE OF ENGINEERING, CHENNAI", font("arialbd.ttf", 44), "white", W)
    centered(d, 120, "Department of Computer Science and Engineering", font("arial.ttf", 36), (200, 220, 240), W)
    centered(d, 190, "CODING CLUB presents", font("arialbd.ttf", 40), (255, 196, 0), W)
    centered(d, 380, "WORKSHOP ON", font("arialbd.ttf", 60), (18, 52, 86), W)
    centered(d, 460, "BUILDING WITH", font("impact.ttf", 110), (200, 60, 40), W)
    centered(d, 590, "OPEN-SOURCE AI", font("impact.ttf", 110), (200, 60, 40), W)
    centered(d, 760, "Resource Person", font("arial.ttf", 38), (90, 90, 90), W)
    centered(d, 820, "Dr. R. Meenakshi", font("arialbd.ttf", 56), (20, 20, 20), W)
    centered(d, 895, "Senior Research Engineer, Chennai AI Labs", font("arial.ttf", 36), (60, 60, 60), W)
    d.rounded_rectangle([140, 1010, W - 140, 1300], 30, fill=(255, 255, 255), outline=(18, 52, 86), width=4)
    f = font("arialbd.ttf", 44)
    d.text((200, 1050), "Date:   14 October 2026", font=f, fill=(20, 20, 20))
    d.text((200, 1130), "Time:   10:00 AM - 1:00 PM", font=f, fill=(20, 20, 20))
    d.text((200, 1210), "Venue:  Seminar Hall 2, Main Block", font=f, fill=(20, 20, 20))
    centered(d, 1380, "All are welcome!", font("arialbd.ttf", 64), (18, 52, 86), W)
    centered(d, 1480, "Bring your laptop. Free registration.", font("arial.ttf", 36), (90, 90, 90), W)
    centered(d, 1580, "Faculty Coordinator: Mrs. S. Revathi, AP/CSE", font("arial.ttf", 32), (90, 90, 90), W)
    im.save(OUT / "poster.jpg", quality=90)


def signature(d, x, y):
    pts = [(x + i * 9, y + random.randint(-12, 12)) for i in range(random.randint(8, 13))]
    d.line(pts, fill=(25, 35, 120), width=3, joint="curve")


def attendance(path, people, start_serial, unsigned=()):
    W, H = 1240, 1754
    im = Image.new("RGB", (W, H), (252, 252, 248))
    d = ImageDraw.Draw(im)
    centered(d, 60, "ATTENDANCE SHEET", font("arialbd.ttf", 44), "black", W)
    centered(d, 120, "Workshop on Building with Open-Source AI  |  14.10.2026", font("arial.ttf", 30), "black", W)
    cols = [60, 160, 560, 800, 960, 1180]
    heads = ["S.No", "Name", "Reg. No", "Dept", "Signature"]
    top, row_h, rows = 200, 64, 22
    for i in range(rows + 2):
        d.line([(cols[0], top + i * row_h), (cols[-1], top + i * row_h)], fill="black", width=2)
    for x in cols:
        d.line([(x, top), (x, top + (rows + 1) * row_h)], fill="black", width=2)
    for i, h in enumerate(heads):
        d.text((cols[i] + 12, top + 16), h, font=font("arialbd.ttf", 28), fill="black")
    for i in range(rows):
        y = top + (i + 1) * row_h
        d.text((cols[0] + 30, y + 16), str(start_serial + i), font=font("arial.ttf", 28), fill="black")
        if i < len(people):
            name, reg = people[i]
            hand = font(random.choice(HANDS), 34)
            ink = random.choice([(20, 30, 110), (15, 15, 15), (30, 40, 140)])
            d.text((cols[1] + 10, y + 12), name, font=hand, fill=ink)
            d.text((cols[2] + 10, y + 12), reg, font=hand, fill=ink)
            d.text((cols[3] + 10, y + 12), reg[2:4], font=hand, fill=ink)
            if start_serial + i not in unsigned:
                signature(d, cols[4] + 30, y + 32)
    # make it look like a phone photo: slight tilt, warm cast, blur, shadow
    im = im.rotate(1.3, expand=True, fillcolor=(120, 110, 95)).filter(ImageFilter.GaussianBlur(0.6))
    shade = Image.linear_gradient("L").resize(im.size).point(lambda v: 255 - v // 6)
    im = Image.composite(im, Image.new("RGB", im.size, (180, 170, 150)), shade)
    im.save(path, quality=85)


def event_photo(path, label, when, gps=True):
    W, H = 1600, 1200
    im = Image.new("RGB", (W, H), (60, 52, 48))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 520], fill=(120, 100, 85))
    d.rectangle([200, 80, 1400, 260], fill=(18, 52, 86))
    centered(d, 120, "Workshop on Building with Open-Source AI", font("arialbd.ttf", 54), "white", W)
    for i in range(14):  # audience
        x, y = 80 + (i % 7) * 220, 640 + (i // 7) * 260
        c = random.choice([(200, 160, 130), (150, 110, 80), (110, 80, 60)])
        d.ellipse([x, y, x + 90, y + 90], fill=c)
        d.rectangle([x - 20, y + 95, x + 110, y + 260], fill=random.choice([(70, 90, 140), (160, 60, 60), (220, 220, 220)]))
    d.text((40, H - 70), label, font=font("arial.ttf", 36), fill=(230, 230, 230))
    exif = Image.Exif()
    exif.get_ifd(0x8769)[36867] = when
    exif[0x010F], exif[0x0110] = "SampleCam", "Phone 12"
    if gps:
        g = exif.get_ifd(0x8825)
        g[1], g[2], g[3], g[4] = "N", (13.0, 0.0, 38.88), "E", (80.0, 14.0, 7.44)
    im.save(path, quality=88, exif=exif)


def main():
    OUT.mkdir(exist_ok=True)
    poster()
    attendance(OUT / "attendance_1.jpg", NAMES[:14], 1, unsigned={9})
    attendance(OUT / "attendance_2.jpg", NAMES[14:], 23)
    event_photo(OUT / "photo_1.jpg", "Inauguration", "2026:10:14 10:08:12")
    event_photo(OUT / "photo_2.jpg", "Hands-on session", "2026:10:14 11:26:40")
    event_photo(OUT / "photo_3.jpg", "Q&A", "2026:10:14 12:41:03", gps=False)
    event_photo(OUT / "photo_4.jpg", "Group photo", "2026:10:14 13:02:55")
    print(f"Samples written to {OUT}")


if __name__ == "__main__":
    main()
