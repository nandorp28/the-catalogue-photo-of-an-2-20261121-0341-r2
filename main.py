#!/usr/bin/env python3
"""Catalogue photo of an impossible gadget: a tin can of DEHYDRATED WATER
with exactly one accessory (a glass of water). Pure-Python stdlib renderer.
Writes /output/entry.png (1024x1024, deterministic)."""
import os
import struct
import sys
import zlib

W = H = 1024

# ---------------------------------------------------------------- 5x7 font
# Each glyph: 7 rows of 5 bits, '#' = on.
FONT = {
    'A': ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    'B': ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    'C': ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    'D': ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    'E': ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    'F': ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    'G': ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    'H': ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    'I': ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    'J': ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    'K': ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    'L': ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    'M': ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    'N': ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    'O': ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    'P': ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    'Q': ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    'R': ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    'S': ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    'T': ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    'U': ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    'V': ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    'W': ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    'X': ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    'Y': ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    'Z': ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    '0': ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    '1': ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    '2': ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    '3': ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    '4': ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    '5': ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    '6': ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    '7': ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    '8': ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    '9': ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    '-': ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    '.': ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ',': ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ':': ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    '!': ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    '(': ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ')': ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    '/': ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    '+': ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    ' ': ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
}


def lerp(a, b, t):
    return a + (b - a) * t


def mix(c1, c2, t):
    return (int(lerp(c1[0], c2[0], t)), int(lerp(c1[1], c2[1], t)),
            int(lerp(c1[2], c2[2], t)))


class Canvas:
    def __init__(self):
        self.px = bytearray(W * H * 3)

    def set(self, x, y, rgb):
        if 0 <= x < W and 0 <= y < H:
            i = (y * W + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = rgb

    def blend(self, x, y, rgb, a):
        if 0 <= x < W and 0 <= y < H:
            i = (y * W + x) * 3
            self.px[i] = int(self.px[i] * (1 - a) + rgb[0] * a)
            self.px[i + 1] = int(self.px[i + 1] * (1 - a) + rgb[1] * a)
            self.px[i + 2] = int(self.px[i + 2] * (1 - a) + rgb[2] * a)

    def rect(self, x0, y0, x1, y1, rgb):
        for y in range(max(0, y0), min(H, y1)):
            base = y * W * 3
            for x in range(max(0, x0), min(W, x1)):
                i = base + x * 3
                self.px[i], self.px[i + 1], self.px[i + 2] = rgb

    def vgrad_rect(self, x0, y0, x1, y1, top, bot):
        for y in range(max(0, y0), min(H, y1)):
            t = (y - y0) / max(1, y1 - y0)
            c = mix(top, bot, t)
            base = y * W * 3
            for x in range(max(0, x0), min(W, x1)):
                i = base + x * 3
                self.px[i], self.px[i + 1], self.px[i + 2] = c

    def ellipse(self, cx, cy, rx, ry, rgb):
        for y in range(max(0, cy - ry), min(H, cy + ry + 1)):
            dy = (y - cy) / ry
            dx = (1 - dy * dy) ** 0.5
            x0 = int(cx - rx * dx)
            x1 = int(cx + rx * dx)
            base = y * W * 3
            for x in range(max(0, x0), min(W, x1 + 1)):
                i = base + x * 3
                self.px[i], self.px[i + 1], self.px[i + 2] = rgb

    def ellipse_blend(self, cx, cy, rx, ry, rgb, a):
        for y in range(max(0, cy - ry), min(H, cy + ry + 1)):
            dy = (y - cy) / ry
            dx = (1 - dy * dy) ** 0.5
            x0 = int(cx - rx * dx)
            x1 = int(cx + rx * dx)
            for x in range(max(0, x0), min(W, x1 + 1)):
                self.blend(x, y, rgb, a)

    def ring(self, cx, cy, rx, ry, rgb, thick=3):
        for y in range(max(0, cy - ry - thick), min(H, cy + ry + thick + 1)):
            for x in range(max(0, cx - rx - thick), min(W, cx + rx + thick + 1)):
                d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
                if 0.92 <= d <= 1.08:
                    self.set(x, y, rgb)

    def line(self, x0, y0, x1, y1, rgb, thick=1):
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for s in range(steps + 1):
            t = s / steps
            x = int(x0 + (x1 - x0) * t)
            y = int(y0 + (y1 - y0) * t)
            for dy in range(-thick // 2, thick // 2 + 1):
                for dx in range(-thick // 2, thick // 2 + 1):
                    self.set(x + dx, y + dy, rgb)

    def poly(self, pts, rgb):
        # filled polygon via scanline
        ys = [p[1] for p in pts]
        for y in range(max(0, min(ys)), min(H, max(ys) + 1)):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    t = (y - y0) / (y1 - y0)
                    xs.append(x0 + (x1 - x0) * t)
            if len(xs) >= 2:
                xs.sort()
                base = y * W * 3
                for x in range(max(0, int(xs[0])), min(W, int(xs[-1]) + 1)):
                    i = base + x * 3
                    self.px[i], self.px[i + 1], self.px[i + 2] = rgb

    def text(self, cx, y, scale, s, rgb, align="center"):
        cw = 6 * scale
        total = len(s) * cw - scale
        x = cx - total // 2 if align == "center" else cx
        for ch in s:
            g = FONT.get(ch, FONT[' '])
            for r in range(7):
                row = g[r]
                for c in range(5):
                    if row[c] == '1':
                        for dy in range(scale):
                            for dx in range(scale):
                                self.set(x + c * scale + dx, y + r * scale + dy, rgb)
            x += cw


def render():
    cv = Canvas()
    # --- studio background: soft vertical gradient + glow behind products
    cv.vgrad_rect(0, 0, W, H, (247, 246, 242), (224, 222, 216))
    cv.ellipse_blend(560, 480, 430, 400, (255, 255, 253), 0.35)
    # floor line + soft floor wash
    for y in range(800, H):
        t = (y - 800) / 224
        c = mix((228, 226, 220), (210, 208, 202), t)
        base = y * W * 3
        for x in range(W):
            i = base + x * 3
            cv.px[i], cv.px[i + 1], cv.px[i + 2] = c
    # soft shadows
    cv.ellipse_blend(430, 800, 240, 26, (60, 58, 52), 0.22)
    cv.ellipse_blend(430, 800, 180, 18, (60, 58, 52), 0.18)
    cv.ellipse_blend(800, 800, 140, 20, (60, 58, 52), 0.20)
    cv.ellipse_blend(800, 800, 100, 13, (60, 58, 52), 0.16)

    # --- the tin can (hero), centre x=430, body y 270..770
    cx, top, bot, hw = 430, 270, 770, 185
    # bottom rim
    cv.ellipse(cx, bot, hw, 42, (120, 124, 130))
    cv.ellipse(cx, bot, hw - 12, 34, (105, 109, 115))
    # metallic body: horizontal gradient with a bright highlight band
    for x in range(cx - hw, cx + hw + 1):
        u = (x - (cx - hw)) / (2 * hw)  # 0..1 across
        # cylinder shading: dark edges, bright band left of centre
        bright = 1.0 - abs(u - 0.38) * 2.2
        bright = max(0.0, min(1.0, bright))
        edge = 1.0 - abs(u - 0.5) * 1.15
        edge = max(0.0, min(1.0, edge))
        base = 178 + 52 * edge
        v = int(base + 42 * bright)
        col = (min(255, v), min(255, v + 3), min(255, v + 8))
        for y in range(top, bot + 1):
            # curve the top/bottom so the body reads as a cylinder
            if y < top + 40:
                dy = (y - top) / 40.0
                if abs(x - cx) > hw * (1 - dy * 0.12):
                    continue
            cv.set(x, y, col)
    # top lid
    cv.ellipse(cx, top, hw, 42, (214, 218, 224))
    cv.ring(cx, top, hw - 14, 34, (150, 155, 162), 3)
    cv.ring(cx, top, hw - 46, 24, (165, 170, 176), 2)
    # pull tab
    cv.ellipse(cx + 30, top - 2, 34, 12, (185, 190, 196))
    cv.ring(cx + 30, top - 2, 26, 8, (140, 145, 152), 2)
    cv.ellipse(cx - 60, top - 6, 20, 8, (235, 238, 242))

    # --- label band (cream, wrapped on the body)
    lx0, lx1, ly0, ly1 = cx - 168, cx + 168, 380, 668
    cv.rect(lx0, ly0, lx1, ly1, (252, 247, 236))
    cv.rect(lx0, ly0, lx1, ly0 + 4, (196, 52, 44))
    cv.rect(lx0, ly1 - 4, lx1, ly1, (196, 52, 44))
    # label text
    ink = (28, 34, 40)
    red = (196, 52, 44)
    cv.text(cx, 396, 3, "AQUA-NADA", (90, 96, 104))
    cv.text(cx, 428, 5, "DEHYDRATED", ink)
    cv.text(cx, 468, 5, "WATER", ink)
    cv.rect(lx0 + 14, 520, lx1 - 14, 556, red)
    cv.text(cx, 526, 3, "JUST ADD WATER", (255, 255, 255))
    cv.text(cx, 570, 2, "NET WT 0 G", (90, 96, 104))
    cv.text(cx, 596, 2, "ADD WATER - STIR - SERVE", ink)
    # barcode
    bx, by = cx - 60, 624
    bars = [3, 2, 5, 2, 3, 4, 2, 3, 2, 6, 2, 3, 4, 2, 5, 2, 3, 2, 4, 3,
            2, 5, 3, 2, 4, 2, 3, 6, 2, 3]
    for wdt in bars:
        cv.rect(bx, by, bx + wdt, by + 26, (20, 22, 26))
        bx += wdt + 2
    # side highlight on the can
    for y in range(top + 44, bot - 4):
        for x in range(cx - 150, cx - 128):
            cv.blend(x, y, (255, 255, 255), 0.18)

    # --- the glass of water (the one accessory), centre x=800
    gx = 800
    # glass walls: tapered trapezoid, darker outline then inner glass
    cv.poly([(gx - 100, 500), (gx + 100, 500), (gx + 76, 790), (gx - 76, 790)],
            (150, 168, 178))
    cv.poly([(gx - 94, 504), (gx + 94, 504), (gx + 71, 786), (gx - 71, 786)],
            (228, 236, 240))
    # water fill
    cv.poly([(gx - 88, 560), (gx + 88, 560), (gx + 70, 782), (gx - 70, 782)],
            (158, 205, 228))
    # water surface ellipse
    cv.ellipse(gx, 560, 88, 12, (196, 226, 240))
    cv.ellipse(gx, 560, 88, 12, (120, 180, 210))
    cv.ellipse(gx, 560, 78, 9, (170, 212, 232))
    # glass rim
    cv.ring(gx, 500, 100, 20, (120, 138, 150), 3)
    # glass highlights + base
    for y in range(510, 780):
        for x in range(gx - 84, gx - 66):
            cv.blend(x, y, (255, 255, 255), 0.35)
    cv.ellipse(gx, 788, 72, 10, (140, 158, 168))
    cv.ellipse(gx, 788, 64, 8, (200, 214, 220))
    return cv


def write_png(path, px, w, h):
    raw = b"".join(b"\x00" + bytes(px[y * w * 3:(y + 1) * w * 3])
                   for y in range(h))

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    data = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(data)
    return len(data)


def out_path():
    if len(sys.argv) > 1 and sys.argv[1] not in ("--check",):
        return sys.argv[1]
    return os.path.join(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"),
                        "entry.png")


def main():
    if "--check" in sys.argv:
        # validate the render without writing: size, format, determinism
        a = render().px
        b = render().px
        assert bytes(a) == bytes(b), "render is not deterministic"
        assert len(a) == W * H * 3
        print(f"check ok: {W}x{H}, deterministic, {len(a)} px bytes")
        return 0
    cv = render()
    path = out_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    n = write_png(path, cv.px, W, H)
    print(f"wrote {path} ({n} bytes, {W}x{H})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
