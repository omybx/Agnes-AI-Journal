#!/usr/bin/env python3
"""
Typewriter Video Generator — Agnes
Converts text input into a retro typewriter-style video using FFmpeg + Pillow.
"""

import os
import sys
import argparse
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ── defaults ──────────────────────────────────────────────────────────────────

DEFAULT_WIDTH        = 800
DEFAULT_HEIGHT       = 400
DEFAULT_FPS          = 12
DEFAULT_MS_PER_CHAR  = 120
DEFAULT_BG_COLOR     = (15, 15, 20)      # deep navy-black
DEFAULT_TEXT_COLOR   = (200, 220, 180)   # warm phosphor green
DEFAULT_CURSOR_COLOR = (200, 220, 180)
DEFAULT_FONT_SIZE    = 36
DEFAULT_FONT_FALLBACK = [
    "C:/Windows/Fonts/lucon.ttf",
    "C:/Windows/Fonts/consola.ttf",
    "C:/Windows/Fonts/cour.ttf",
    None,
]
OUTPUT_DIR  = Path("creative_works")
TEMP_DIR    = Path("creative_works/_typewriter_frames")


# ── helpers ───────────────────────────────────────────────────────────────────

def find_font(size: int) -> ImageFont.FreeTypeFont:
    for path in DEFAULT_FONT_FALLBACK:
        if path and os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()

def typewriter_frame(
    text: str,
    char_count: int,
    *,
    width, height,
    bg_color,
    text_color,
    cursor_color,
    font,
    cursor_blink: bool = True,
) -> Image.Image:
    """Render one frame of the typewriter animation."""
    img  = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    visible = text[:char_count]
    if char_count < len(text):
        visible += "_"   # pending char indicator

    # center the text block
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    margin = 60
    x = max(margin, (width - text_w) // 2)
    y = max(margin, (height - text_h) // 2 - 20)

    draw.text((x, y), visible, fill=text_color, font=font)

    # blinking cursor after current position
    if cursor_blink:
        cur_bbox = draw.textbbox((x, y), visible, font=font)
        cur_x = cur_bbox[2]
        cur_y = cur_bbox[1]
        # small blinking block cursor
        draw.rectangle([cur_x, cur_y, cur_x + 10, cur_y + (text_h or size)], fill=cursor_color)

    return img


def generate_typewriter_video(
    text: str,
    output_path: str,
    *,
    width       = DEFAULT_WIDTH,
    height      = DEFAULT_HEIGHT,
    fps         = DEFAULT_FPS,
    ms_per_char = DEFAULT_MS_PER_CHAR,
    bg_color    = DEFAULT_BG_COLOR,
    text_color  = DEFAULT_TEXT_COLOR,
    cursor_color = DEFAULT_CURSOR_COLOR,
    font_size   = DEFAULT_FONT_SIZE,
):
    """
    Build a typewriter video from `text` and save to `output_path`.

    Uses a two-phase approach:
      Phase 1 — typing: one frame per character revealed, then hold.
      Phase 2 — hold:   final frame held for ~1.5 seconds before looping / end.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    output_path = str(OUTPUT_DIR / output_path)

    font = find_font(font_size)

    # clean previous frames
    for f in TEMP_DIR.glob("frame_*.png"):
        f.unlink()

    n        = len(text)
    hold_fps = int(fps * 1.5)   # frames to hold final frame

    frame_num = 0

    # ── typing phase ──────────────────────────────────────────────────────────
    for i in range(n + 1):
        frame = typewriter_frame(
            text, i,
            width=width, height=height,
            bg_color=bg_color, text_color=text_color,
            cursor_color=cursor_color, font=font,
        )
        frame_path = TEMP_DIR / f"frame_{frame_num:05d}.png"
        frame.save(frame_path)
        frame_num += 1

    # ── hold phase — repeat last frame ───────────────────────────────────────
    last_frame = TEMP_DIR / f"frame_{frame_num - 1:05d}.png"
    for _ in range(hold_fps):
        frame = Image.open(last_frame)
        frame_path = TEMP_DIR / f"frame_{frame_num:05d}.png"
        frame.save(frame_path)
        frame_num += 1

    # ── compile with FFmpeg ───────────────────────────────────────────────────
    input_glob = str(TEMP_DIR / "frame_%05d.png").replace("\\", "/")
    ffmpeg_cmd  = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", input_glob,
        "-c:v", "libx264",
        "-preset", "fast",
        "-pix_fmt", "yuv420p",
        "-frames:v", str(frame_num),
        output_path,
    ]

    import subprocess
    result = subprocess.run(
        ffmpeg_cmd,
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"FFmpeg stderr:\n{result.stderr}", file=sys.stderr)
        raise RuntimeError(f"FFmpeg failed with code {result.returncode}")

    # clean temp frames
    for f in TEMP_DIR.glob("frame_*.png"):
        f.unlink()

    return output_path


# ── CLI entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Typewriter video generator")
    p.add_argument("-t", "--text",   default="Hello, world! Agnes is typing...")
    p.add_argument("-o", "--output", default="typewriter_demo.mp4")
    p.add_argument("--width",  type=int, default=DEFAULT_WIDTH)
    p.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    p.add_argument("--fps",    type=int, default=DEFAULT_FPS)
    p.add_argument("--ms",     type=int, default=DEFAULT_MS_PER_CHAR,
                   help="milliseconds per character")
    args = p.parse_args()

    out_path = generate_typewriter_video(
        args.text,
        args.output,
        width=args.width,
        height=args.height,
        fps=args.fps,
        ms_per_char=args.ms,
    )
    print(f"✓ Video saved: {out_path}")