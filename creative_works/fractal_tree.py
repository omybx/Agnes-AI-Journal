"""
fractal_tree.py
 Generates an animated fractal/tree video using Pillow + FFmpeg.
 Branches grow recursively from a trunk, sway gently, and cycle through
 a warm amber-to-teal palette as time progresses.
"""

import math, subprocess, os, sys, json
from PIL import Image, ImageDraw

# ── Config ────────────────────────────────────────────────────────────────────
W, H            = 960, 720
FPS             = 24
DURATION        = 12          # seconds
TOTAL_FRAMES    = FPS * DURATION
TRUNK_LEN       = 160
BRANCH_ANGLE    = 28          # degrees
DEPTH           = 9           # recursion depth
BRANCH_SHRINK   = 0.72        # length multiplier per level
SWAY_AMP        = 6           # max sway offset in pixels
Sway_Hz         = 0.28        # sway oscillation (Hz)
PALETTE_CYCLE   = 6.0         # seconds for full palette rotation

# Output
OUT_DIR  = os.path.dirname(os.path.abspath(__file__))
WORK_DIR = os.path.join(OUT_DIR, "_fractal_frames")
OUT_MP4  = os.path.join(OUT_DIR, "fractal_tree.mp4")

os.makedirs(WORK_DIR, exist_ok=True)

# ── Helpers ───────────────────────────────────────────────────────────────────

def lerp_color(c1, c2, t):
    """Linear interpolate between two RGB triples."""
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def palette_at(progress):
    """
    Return (branch_col, tip_col, bg_col) for a given 0-1 progress value.
    Palette slowly rotates through 4 moods.
    """
    moods = [
        # branch_col, tip_col, bg_col
        ((200, 120,  30), (255, 220,  80), (10,  8, 18)),   # warm amber/night
        (( 40, 160, 120), ( 80, 240, 180), ( 5, 12, 14)),   # teal/midnight
        ((180,  50, 100), (255, 120, 180), (12,  5, 15)),   # magenta/void
        (( 60, 100, 200), (120, 200, 255), ( 5,  8, 20)),   # blue/deep
    ]
    t = (progress * PALETTE_CYCLE) % 1.0
    slot = int(t * len(moods))
    next_slot = (slot + 1) % len(moods)
    local = (t * len(moods)) - slot   # 0-1 within current slot

    def _mix(c1, c2, lt):
        return tuple(int(a + (b - a) * lt) for a, b in zip(c1, c2))

    branch = _mix(moods[slot][0], moods[next_slot][0], local)
    tip    = _mix(moods[slot][1], moods[next_slot][1], local)
    bg     = _mix(moods[slot][2], moods[next_slot][2], local)
    return branch, tip, bg


def draw_branch(draw, x, y, angle, length, depth, t, sway_offset):
    """Recursively draw one branch and return list of tip points for tips layer."""
    if depth == 0 or length < 2:
        return [(x, y)]

    # Sway: deeper branches sway more
    sway = sway_offset * (1 - depth / DEPTH) * (math.pi / 180)
    effective_angle = math.radians(angle + sway)

    x2 = x + length * math.sin(effective_angle)
    y2 = y - length * math.cos(effective_angle)

    # Width tapers with depth
    width = max(1, int(3.5 * (depth / DEPTH) ** 1.2))

    # Color: branch vs tip
    branch_ratio = (DEPTH - depth) / DEPTH   # 0=trunk, 1=tip
    branch_col, tip_col, _ = palette_at(t)
    col = lerp_color(tip_col, branch_col, branch_ratio)

    draw.line([(x, y), (x2, y2)], fill=col, width=width)

    # Recurse
    new_angle = math.degrees(effective_angle)
    tips = []
    tips += draw_branch(draw, x2, y2, new_angle - BRANCH_ANGLE,
                         length * BRANCH_SHRINK, depth - 1, t, sway_offset)
    tips += draw_branch(draw, x2, y2, new_angle + BRANCH_ANGLE,
                         length * BRANCH_SHRINK, depth - 1, t, sway_offset)
    return tips


def draw_leaf_tips(draw, tips, t):
    """Scatter small glowing circles at branch tips."""
    branch_col, tip_col, _ = palette_at(t)
    n_tips = len(tips)
    for i, (x, y) in enumerate(tips):
        phase = (i / max(1, n_tips)) * math.pi * 2
        pulse = 0.5 + 0.5 * math.sin(phase + t * 4)
        r = int(2 + pulse * 2)
        alpha = int(180 + 75 * pulse)
        col = lerp_color(tip_col, (255, 255, 255), pulse * 0.4)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=col)


def render_frame(frame_idx):
    t = frame_idx / TOTAL_FRAMES
    sway_offset = SWAY_AMP * math.sin(2 * math.pi * Sway_Hz * (frame_idx / FPS))
    progress = frame_idx / TOTAL_FRAMES

    branch_col, tip_col, bg_col = palette_at(t)

    img = Image.new("RGB", (W, H), bg_col)
    draw = ImageDraw.Draw(img)

    # Soft radial vignette
    for r in range(80, 0, -1):
        alpha = int(4 * (1 - r / 80))
        if alpha > 0:
            draw.ellipse([W//2 - r, H - 60 - r, W//2 + r, H - 60 + r],
                         fill=lerp_color(bg_col, (0, 0, 0), alpha / 30))

    # Ground line
    ground_y = H - 60
    draw.ellipse([W//2 - 6, ground_y - 6, W//2 + 6, ground_y + 6],
                 fill=lerp_color(branch_col, tip_col, 0.5))

    # Draw tree
    trunk_x = W // 2
    trunk_y = ground_y
    tips = draw_branch(draw, trunk_x, trunk_y,
                       0, TRUNK_LEN, DEPTH, progress, sway_offset)

    # Leaf glow on tips
    draw_leaf_tips(draw, tips, t)

    return img


def main():
    print(f"Generating {TOTAL_FRAMES} frames → {OUT_MP4}")
    print(f"  {W}x{H} @ {FPS}fps, {DURATION}s duration")
    print(f"  Branch depth={DEPTH}, angle={BRANCH_ANGLE}°, shrink={BRANCH_SHRINK}")

    for i in range(TOTAL_FRAMES):
        frame_path = os.path.join(WORK_DIR, f"frame_{i:04d}.png")
        img = render_frame(i)
        img.save(frame_path)
        if (i + 1) % 24 == 0:
            print(f"  [{i+1:4d}/{TOTAL_FRAMES}] frame saved")

    print("Frames done. Compiling with FFmpeg...")

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", os.path.join(WORK_DIR, "frame_%04d.png"),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        OUT_MP4
    ]
    result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("FFmpeg error:", result.stderr[-800:])
        sys.exit(1)

    size_kb = os.path.getsize(OUT_MP4) // 1024
    print(f"\n✓ fractal_tree.mp4 — {size_kb} KB")

    # Verify with ffprobe
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_streams", OUT_MP4],
        capture_output=True, text=True
    )
    try:
        info = json.loads(probe.stdout)
        vid = next(s for s in info["streams"] if s["codec_type"] == "video")
        print(f"  {vid['width']}x{vid['height']} @ {vid['r_frame_rate']} fps, "
              f"{vid['nb_frames']} frames")
    except Exception as e:
        print(f"  ffprobe: {e}")


if __name__ == "__main__":
    main()