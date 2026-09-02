#!/usr/bin/env python3
"""
ASCII Nebula Generator — Agnes
Renders a drifting ASCII-art nebula rendered frame-by-frame using Pillow,
then compiles into an MP4 with FFmpeg. The nebula breathes: stars pulse
with a sine wave, the color palette cycles through deep-space hues, and
ASCII characters drift with parallax depth layers.

Each frame is drawn into a Pillow Image using a monospace font so the
character grid stays perfectly aligned. FFmpeg then assembles them.
"""

import os
import sys
import math
import argparse
import shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ── output dirs ────────────────────────────────────────────────────────────────
OUTPUT_DIR = Path("creative_works")
TEMP_DIR   = OUTPUT_DIR / "_nebula_frames"

# ── defaults ──────────────────────────────────────────────────────────────────
DEFAULT_WIDTH    = 960
DEFAULT_HEIGHT   = 540
DEFAULT_FPS      = 18
DEFAULT_DURATION = 12        # seconds
DEFAULT_FONT     = "C:/Windows/Fonts/lucon.ttf"

# Characters that read as "space dust" — the denser ones toward the end
STAR_CHARS = list(" ·,:;+xX#$@")

# Pre-built palette: (R, G, B) for each color zone
COLOR_CYCLES = [
    # cold blue-violet nebula
    [(30, 20, 80),  (60, 30, 130), (100, 50, 180), (150, 80, 220)],
    # warm amber-crimson nebula
    [(80, 20, 30),  (140, 40, 60), (200, 80, 100), (240, 160, 120)],
    # teal-cyan depths
    [(10, 50, 80),  (20, 90, 140), (40, 150, 200), (100, 220, 240)],
]

# ── font loader ───────────────────────────────────────────────────────────────
def find_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        DEFAULT_FONT,
        "C:/Windows/Fonts/consola.ttf",
        "C:/Windows/Fonts/cour.ttf",
        "C:/Windows/Fonts/msgothic.ttc",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()

# ── star field ────────────────────────────────────────────────────────────────
class Star:
    """A single drifting star in the ASCII grid."""
    __slots__ = ("gx", "gy", "depth", "phase", "speed")

    def __init__(self, grid_w: int, grid_h: int):
        # grid position (floats for smooth drift)
        self.gx     = (grid_w - 1) * (0.1 + 0.8 * _rand())
        self.gy     = (grid_h - 1) * (0.1 + 0.8 * _rand())
        # depth: 1.0 = foreground (fast, bright), 0.1 = background
        self.depth  = 0.1 + 0.9 * _rand()
        # phase offset so stars don't pulse in sync
        self.phase  = _rand() * math.tau
        # drift speed (cells per second)
        self.speed  = (0.5 + _rand()) * self.depth


# tiny LCG so star field is reproducible but not uniform
_lcg_state = 42
def _rand() -> float:
    global _lcg_state
    _lcg_state = (_lcg_state * 1664525 + 1013904223) & 0xFFFFFFFF
    return (_lcg_state >> 8) / 16777215.0

def build_stars(grid_w: int, grid_h: int, seed: int = 0) -> list:
    global _lcg_state
    _lcg_state = seed
    count = int(grid_w * grid_h * 0.09)   # ~9% fill rate
    return [Star(grid_w, grid_h) for _ in range(count)]

# ── color helpers ─────────────────────────────────────────────────────────────
def blend(a, b, t: float):
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))

def palette_color(palette, t: float):
    """Return a color interpolated across a 4-stop gradient."""
    t = max(0.0, min(1.0, t))
    seg = t * (len(palette) - 1)
    i   = int(seg)
    f   = seg - i
    i   = min(i, len(palette) - 2)
    return blend(palette[i], palette[i + 1], f)

# ── render one frame ─────────────────────────────────────────────────────────
def render_frame(
    stars: list,
    t: float,
    *,
    img_w: int,
    img_h: int,
    font,
    char_w: int,
    char_h: int,
    grid_w: int,
    grid_h: int,
    palette_cycle: list,
    bg_base: tuple,
) -> Image.Image:
    """
    Draw the nebula at time `t` (seconds) into an Image.
    Stars drift with parallax depth; brightness pulses with a sine wave.
    Background gets a subtle radial glow.
    """
    img  = Image.new("RGB", (img_w, img_h), bg_base)
    draw = ImageDraw.Draw(img)

    palette = palette_cycle[int(t / 12) % len(palette_cycle)]

    # ── background glow: radial gradient via overlapping ellipses ──
    cx, cy = img_w // 2, img_h // 2
    glows = [
        (cx, cy, img_w // 2,      img_h // 2,     (30, 30, 60,  80)),
        (cx, cy, img_w // 3,      img_h // 3,     (50, 40, 90,  60)),
        (cx, cy, img_w // 5,      img_h // 5,     (70, 60, 120, 40)),
    ]
    for gx, gy, rw, rh, col in glows:
        overlay = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
        go = ImageDraw.Draw(overlay)
        go.ellipse([gx - rw, gy - rh, gx + rw, gy + rh], fill=col)
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    # ── star layer (re-draw after alpha composite) ──
    draw = ImageDraw.Draw(img)

    for s in stars:
        # drift with parallax
        dx = s.speed * t * 0.05
        sx = (s.gx + dx) % grid_w
        sy = (s.gy + s.speed * t * 0.02) % grid_h

        # pulse brightness with depth-dependent frequency
        freq  = 0.8 + s.depth * 1.4
        pulse = 0.5 + 0.5 * math.sin(t * freq + s.phase)
        bri   = int(30 + pulse * 70 * s.depth)

        # color: background stars cool/blue, foreground warm/white
        temp_t = s.depth * 0.6 + pulse * 0.4
        base   = palette_color(palette, temp_t)
        col    = tuple(min(255, int(c * bri / 100)) for c in base)

        # char index by depth
        ci = min(int(s.depth * (len(STAR_CHARS) - 1)), len(STAR_CHARS) - 1)
        ch = STAR_CHARS[ci]

        px = int(sx * char_w)
        py = int(sy * char_h)
        draw.text((px, py), ch, fill=col, font=font)

    return img

# ── main ───────────────────────────────────────────────────────────────────────
def generate_nebula(
    seed_text: str  = "nebula",
    output_name: str = "ascii_nebula.mp4",
    *,
    width:    int = DEFAULT_WIDTH,
    height:   int = DEFAULT_HEIGHT,
    fps:      int = DEFAULT_FPS,
    duration: int = DEFAULT_DURATION,
    font_path: str = DEFAULT_FONT,
) -> str:
    """
    Generate a drifting ASCII nebula video.

    seed_text  — drives the LCG star-field seed (different text = different star layout)
    output_name — filename inside creative_works/
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    # ── font and grid metrics ──
    font  = find_font(font_size_for_dim(width, height))
    # measure one "cell" using the font's actual glyph advance
    test_img = Image.new("RGB", (1, 1))
    td       = ImageDraw.Draw(test_img)
    bbox     = td.textbbox((0, 0), "W", font=font)  # 'W' is usually wide
    char_w   = max(bbox[2] - bbox[0], 1)
    char_h   = max(bbox[3] - bbox[1], 1)

    grid_w = max(1, width  // char_w)
    grid_h = max(1, height // char_h)

    # use seed_text to derive a deterministic star field
    seed = sum(ord(c) * (i + 1) for i, c in enumerate(seed_text))

    stars = build_stars(grid_w, grid_h, seed=seed)

    # ── render frames ──
    total_frames = fps * duration
    for frame_idx in range(total_frames):
        t = frame_idx / fps
        bg_base = (8, 6, 18)   # deep space black-blue

        frame = render_frame(
            stars, t,
            img_w=width, img_h=height,
            font=font,
            char_w=char_w, char_h=char_h,
            grid_w=grid_w, grid_h=grid_h,
            palette_cycle=COLOR_CYCLES,
            bg_base=bg_base,
        )

        out_path = TEMP_DIR / f"frame_{frame_idx:05d}.png"
        frame.save(out_path)

        if frame_idx % fps == 0:
            print(f"  [{t:5.1f}s] frame {frame_idx}/{total_frames}")

    # ── compile with FFmpeg ──────────────────────────────────────────────────
    input_glob = str(TEMP_DIR / "frame_%05d.png").replace("\\", "/")
    out_full   = str(OUTPUT_DIR / output_name)

    import subprocess
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i",         input_glob,
        "-c:v",       "libx264",
        "-preset",    "fast",
        "-pix_fmt",   "yuv420p",
        out_full,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("FFmpeg stderr:", result.stderr, file=sys.stderr)
        raise RuntimeError(f"FFmpeg failed: {result.returncode}")

    # clean temp frames
    shutil.rmtree(TEMP_DIR, ignore_errors=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n✓ Nebula saved: {out_full}  ({duration}s, {fps}fps, {width}×{height})")
    return out_full

def font_size_for_dim(w: int, h: int) -> int:
    base = min(w, h)
    return max(8, min(14, base // 80))

# ── CLI ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    p = argparse.ArgumentParser(description="ASCII Nebula video generator")
    p.add_argument("-t", "--text",     default="nebula seed 2026",
                   help="seed text (affects star field layout)")
    p.add_argument("-o", "--output",   default="ascii_nebula.mp4")
    p.add_argument("-W", "--width",    type=int, default=DEFAULT_WIDTH)
    p.add_argument("-H", "--height",   type=int, default=DEFAULT_HEIGHT)
    p.add_argument("-f", "--fps",      type=int, default=DEFAULT_FPS)
    p.add_argument("-d", "--duration", type=int, default=DEFAULT_DURATION)
    args = p.parse_args()

    out = generate_nebula(
        seed_text   = args.text,
        output_name = args.output,
        width       = args.width,
        height      = args.height,
        fps         = args.fps,
        duration    = args.duration,
    )
    print(f"\nOutput: {out}")