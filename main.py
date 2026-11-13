#!/usr/bin/env python3
"""Coolest-art-01 entry: "Neon Horizon".

A lone traveller stands on a glowing grid plain beneath a huge striped
synthwave sun, between two mountain ridges, under a violet starfield.
Drawn entirely by this program, pixel by pixel, with the Python standard
library only (no PIL, no network, no external files). Deterministic: the
same seed always produces the same bytes.

Run it:
    mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
It writes /output/entry.png (or $MAKEFUN_OUTPUT_DIR/entry.png): a
1024x1024 PNG, well under 1 MiB.
"""

import math
import os
import random
import struct
import zlib

W = H = 1024
HORIZON = 640
SUN_CX, SUN_CY, SUN_R = 512, 520, 220
SEED = 20261113

# ---------------------------------------------------------------- palette
SKY_STOPS = [  # (y, (r, g, b)) — vertical sky gradient
    (0, (24, 8, 44)),
    (220, (58, 20, 96)),
    (420, (122, 28, 110)),
    (560, (198, 48, 92)),
    (HORIZON, (255, 107, 53)),
]
SUN_STOPS = [  # (y, (r, g, b)) — vertical gradient inside the sun disc
    (SUN_CY - SUN_R, (255, 226, 89)),
    (SUN_CY, (255, 167, 81)),
    (SUN_CY + SUN_R, (255, 46, 136)),
]
FAR_MOUNTAIN = (52, 26, 88)
NEAR_MOUNTAIN = (18, 8, 40)
FLOOR_TOP = (26, 15, 51)
FLOOR_BOTTOM = (8, 5, 18)
GRID_CYAN = (0, 240, 255)
GRID_PINK = (255, 60, 140)
REFLECT = (255, 130, 70)
FIGURE = (10, 6, 24)


def lerp(a, b, t):
    return a + (b - a) * t


def grad_color(stops, y):
    """Linear interpolation of an (r, g, b) gradient at row y."""
    if y <= stops[0][0]:
        return stops[0][1]
    for (y0, c0), (y1, c1) in zip(stops, stops[1:]):
        if y <= y1:
            t = (y - y0) / (y1 - y0)
            return (
                round(lerp(c0[0], c1[0], t)),
                round(lerp(c0[1], c1[1], t)),
                round(lerp(c0[2], c1[2], t)),
            )
    return stops[-1][1]


def mix(c0, c1, t):
    return (
        round(lerp(c0[0], c1[0], t)),
        round(lerp(c0[1], c1[1], t)),
        round(lerp(c0[2], c1[2], t)),
    )


def row_bytes(color, width=W):
    return bytes(color) * width


def put_pixel(buf, x, y, color):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        buf[i] = color[0]
        buf[i + 1] = color[1]
        buf[i + 2] = color[2]


def hspan(buf, y, x0, x1, color):
    """Fill a horizontal span of row y with a solid color."""
    x0 = max(0, x0)
    x1 = min(W - 1, x1)
    if x1 < x0:
        return
    i0 = (y * W + x0) * 3
    buf[i0:(y * W + x1 + 1) * 3] = bytes(color) * (x1 - x0 + 1)


def disc(buf, cx, cy, r, color):
    """Fill a solid disc (row spans)."""
    for y in range(max(0, cy - r), min(H - 1, cy + r) + 1):
        dy = y - cy
        hw = int(math.sqrt(max(0, r * r - dy * dy)))
        hspan(buf, y, cx - hw, cx + hw, color)


def ridge_fn(base, terms, notch, notch_w):
    """A mountain ridge: y(x) = base + sine bumps + a valley notch at centre.

    terms: list of (amplitude, frequency, phase). The notch pushes the
    ridge down (larger y) near x=512 so the sun shines through a valley.
    """
    out = []
    for x in range(W):
        y = base
        for amp, freq, ph in terms:
            y += amp * math.sin(x * freq + ph)
        y += notch * math.exp(-(((x - 512) / notch_w) ** 2))
        out.append(y)
    return out


def fill_ridge(buf, ridge, y_bottom, color):
    """Fill the area between a ridge and y_bottom, row by row.

    For each row, scan the ridge list once and fill the contiguous runs
    where the ridge sits at or above the row.
    """
    top = int(min(ridge))
    for y in range(max(0, top), min(H - 1, y_bottom) + 1):
        in_run = False
        start = 0
        for x in range(W):
            inside = ridge[x] <= y
            if inside and not in_run:
                start = x
                in_run = True
            elif not inside and in_run:
                hspan(buf, y, start, x - 1, color)
                in_run = False
        if in_run:
            hspan(buf, y, start, W - 1, color)


def png_bytes(rgb):
    """Encode a W*H*3 bytearray as a PNG (filter 0, zlib level 9)."""
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)
        raw += rgb[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(typ, data):
        c = struct.pack(">I", len(data)) + typ + data
        return c + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", comp)
        + chunk(b"IEND", b"")
    )


def main():
    rng = random.Random(SEED)
    buf = bytearray(W * H * 3)

    # --- sky: one precomputed colour per row, filled with C-speed slices
    sky_rows = [grad_color(SKY_STOPS, y) for y in range(H)]
    for y in range(HORIZON):
        i0 = y * W * 3
        buf[i0:i0 + W * 3] = row_bytes(sky_rows[y])

    # --- stars in the upper sky (seeded, deterministic)
    stars = []
    for _ in range(190):
        stars.append((rng.randrange(0, W), rng.randrange(0, 560),
                      rng.choice([1, 1, 1, 2]), rng.random()))
    for x, y, size, bright in stars:
        c = (round(200 + 55 * bright), round(190 + 55 * bright),
             round(230 + 25 * bright))
        put_pixel(buf, x, y, c)
        if size == 2:
            put_pixel(buf, x + 1, y, c)
            put_pixel(buf, x, y + 1, c)
            put_pixel(buf, x + 1, y + 1, c)

    # --- shooting star, upper right
    sx, sy = 700, 118
    for k in range(26):
        t = k / 25
        x = sx + int(k * 2.2)
        y = sy + int(k * 1.1)
        b = round(255 * (1 - t))
        put_pixel(buf, x, y, (b, b, min(255, b + 30)))

    # --- glow rings around the sun (soft halo, drawn before the disc)
    for r, alpha in ((252, 0.30), (292, 0.18), (340, 0.10)):
        for y in range(max(0, SUN_CY - r), min(HORIZON - 1, SUN_CY + r) + 1):
            dy = y - SUN_CY
            hw = int(math.sqrt(max(0, r * r - dy * dy)))
            hspan(buf, y, SUN_CX - hw, SUN_CX + hw,
                  mix(sky_rows[y], (255, 90, 150), alpha))

    # --- the sun, with horizontal slits widening toward its base
    slits = [(522, 527), (540, 549), (568, 582), (600, 622)]
    for y in range(SUN_CY - SUN_R, min(HORIZON, SUN_CY + SUN_R) + 1):
        if any(a <= y <= b for a, b in slits):
            continue
        dy = y - SUN_CY
        hw = int(math.sqrt(max(0, SUN_R * SUN_R - dy * dy)))
        hspan(buf, y, SUN_CX - hw, SUN_CX + hw, grad_color(SUN_STOPS, y))

    # --- birds: two small pale chevrons in the sky
    for bx, by in ((205, 185), (262, 152)):
        for dx in range(-7, 8):
            put_pixel(buf, bx + dx, by + abs(dx) // 2, (205, 185, 225))
            put_pixel(buf, bx + dx, by + abs(dx) // 2 + 1, (205, 185, 225))

    # --- mountains, far then near (the near one has the deeper valley)
    far = ridge_fn(600, [(18, 0.011, 1.7), (12, 0.023, 0.4),
                         (8, 0.041, 2.9), (5, 0.067, 1.1)], 26, 200)
    fill_ridge(buf, far, HORIZON, FAR_MOUNTAIN)
    near = ridge_fn(622, [(26, 0.009, 4.1), (16, 0.019, 1.2),
                          (10, 0.037, 0.7), (4, 0.083, 2.0)], 44, 150)
    fill_ridge(buf, near, HORIZON, NEAR_MOUNTAIN)

    # --- floor: dark gradient, lighter near the horizon
    for y in range(HORIZON, H):
        t = (y - HORIZON) / (H - HORIZON)
        c = mix(FLOOR_TOP, FLOOR_BOTTOM, t)
        i0 = y * W * 3
        buf[i0:i0 + W * 3] = row_bytes(c)

    # --- the sun's warm reflection on the floor (soft vertical band)
    prof = [math.exp(-(((x - 512) / 85) ** 2)) for x in range(512 - 170, 513 + 170)]
    for y in range(HORIZON + 1, H):
        alpha = 0.5 * (1 - (y - HORIZON) / (H - HORIZON) * 0.75)
        if alpha <= 0.01:
            continue
        for k, p in enumerate(prof):
            a = alpha * p
            if a < 0.02:
                continue
            x = 512 - 170 + k
            i = (y * W + x) * 3
            buf[i] = round(buf[i] + (REFLECT[0] - buf[i]) * a)
            buf[i + 1] = round(buf[i + 1] + (REFLECT[1] - buf[i + 1]) * a)
            buf[i + 2] = round(buf[i + 2] + (REFLECT[2] - buf[i + 2]) * a)

    # --- perspective grid: verticals converging on the vanishing point
    for i in range(-8, 9):
        for y in range(HORIZON + 1, H):
            t = (y - HORIZON) / (H - HORIZON)
            spread = 26 + t * 130
            x = int(512 + i * spread)
            bright = 0.55 + 0.45 * t
            c = mix(GRID_PINK, GRID_CYAN, abs(i) / 8)
            c = (round(c[0] * bright), round(c[1] * bright),
                 round(c[2] * bright))
            put_pixel(buf, x, y, c)
            put_pixel(buf, x + 1, y, c)

    # --- perspective grid: horizontals, spacing growing toward the viewer
    hy, gap = HORIZON + 8, 10
    k = 0
    while hy < H:
        bright = 0.45 + 0.55 * (hy - HORIZON) / (H - HORIZON)
        for x in range(W):
            c = mix(GRID_PINK, GRID_CYAN, abs(x - 512) / 512)
            put_pixel(buf, x, hy,
                      (round(c[0] * bright), round(c[1] * bright),
                       round(c[2] * bright)))
            put_pixel(buf, x, hy + 1,
                      (round(c[0] * bright), round(c[1] * bright),
                       round(c[2] * bright)))
        gap = int(gap * 1.55) + 2
        hy += gap
        k += 1

    # --- the lone traveller on the horizon, silhouetted against the sun
    disc(buf, 512, 604, 7, FIGURE)
    for y in range(612, HORIZON + 1):
        t = (y - 612) / (HORIZON - 612)
        hw = round(lerp(10, 5, t))
        hspan(buf, y, 512 - hw, 512 + hw, FIGURE)
    for y in range(630, HORIZON + 1):
        hspan(buf, y, 504, 508, FIGURE)
        hspan(buf, y, 516, 520, FIGURE)

    # --- write the PNG
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "entry.png"), "wb") as f:
        f.write(png_bytes(buf))


if __name__ == "__main__":
    main()
