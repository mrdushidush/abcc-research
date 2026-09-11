#!/usr/bin/env python3
"""Decode a sixel stream to PNG. A read-only instrument: it draws what a sixel
terminal would draw, so a picture can be looked at without one.

Not a general decoder -- it handles what abcc's encoder emits: RGB palette
definitions, run-length repeats, `$` carriage return, `-` newline. It raises on
anything else rather than guessing, because a decoder that silently skips is an
instrument that lies.
"""
import re
import sys

from PIL import Image

ESC = 0x1B
ST = bytes([ESC, 0x5C])  # ESC backslash


def decode(data: bytes) -> Image.Image:
    m = re.search(rb"\x1bP[0-9;]*q", data)
    if not m:
        raise SystemExit("no sixel introducer (ESC P ... q) found")
    body = data[m.end() :]
    end = body.find(ST)
    if end >= 0:
        body = body[:end]

    ra = re.match(rb'"(\d+);(\d+);(\d+);(\d+)', body)
    if not ra:
        raise SystemExit("no raster attributes; refusing to guess the size")
    w, h = int(ra.group(3)), int(ra.group(4))
    body = body[ra.end() :]

    px = [[(0, 0, 0)] * w for _ in range(h)]
    pal: dict[int, tuple[int, int, int]] = {}
    cur = (255, 255, 255)
    x = band = 0
    i, n = 0, len(body)
    while i < n:
        c = body[i]
        if c == 0x23:  # '#' -- define and/or select a colour
            m2 = re.match(rb"#(\d+)(?:;(\d+);(\d+);(\d+);(\d+))?", body[i:])
            idx = int(m2.group(1))
            if m2.group(2) is not None:
                if int(m2.group(2)) != 2:
                    raise SystemExit(f"colour space {m2.group(2)!r} is not RGB")
                pal[idx] = tuple(
                    round(int(m2.group(k)) * 255 / 100) for k in (3, 4, 5)
                )
            cur = pal.get(idx, (255, 255, 255))
            i += m2.end()
        elif c == 0x21:  # '!' -- run length
            m2 = re.match(rb"!(\d+)(.)", body[i:], re.DOTALL)
            rep, ch = int(m2.group(1)), m2.group(2)[0]
            _emit(px, cur, x, band, ch, rep, w, h)
            x += rep
            i += m2.end()
        elif c == 0x24:  # '$' -- graphics carriage return
            x = 0
            i += 1
        elif c == 0x2D:  # '-' -- graphics newline
            x = 0
            band += 1
            i += 1
        elif 0x3F <= c <= 0x7E:
            _emit(px, cur, x, band, c, 1, w, h)
            x += 1
            i += 1
        elif c in (0x0A, 0x0D, 0x20):
            i += 1
        else:
            raise SystemExit(f"unexpected byte {c:#x} at offset {i}")

    im = Image.new("RGB", (w, h))
    im.putdata([p for row in px for p in row])
    return im


def _emit(px, colour, x, band, ch, rep, w, h) -> None:
    bits = ch - 0x3F
    if bits == 0:
        return
    for k in range(6):
        if not bits & (1 << k):
            continue
        y = band * 6 + k
        if not 0 <= y < h:
            continue
        row = px[y]
        for dx in range(rep):
            if 0 <= x + dx < w:
                row[x + dx] = colour


if __name__ == "__main__":
    with open(sys.argv[1], "rb") as fh:
        img = decode(fh.read())
    img.save(sys.argv[2])
    print(f"{sys.argv[2]}  {img.size[0]}x{img.size[1]}")
