#!/usr/bin/env python3
"""
Constellation Map Generator — Agnes
Renders a visual constellation map from today's intention keywords.
Each intention becomes a star; related intentions are connected by constellation lines.
Categories determine color zones; semantic similarity draws the connections.

Output: both ASCII art (terminal) and PNG/MP4 (visual) formats.
"""

import os
import sys
import json
import math
import random
import argparse
import shutil
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ── paths ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
INTENTIONS_FILE = ROOT / "intentions.json"
OUTPUT_DIR = ROOT / "creative_works"
TEMP_DIR = OUTPUT_DIR / "_constellation_frames"

# ── defaults ──────────────────────────────────────────────────────────────────
DEFAULT_WIDTH = 1200
DEFAULT_HEIGHT = 800
DEFAULT_FPS = 18
DEFAULT_DURATION = 10
DEFAULT_FONT = "C:/Windows/Fonts/lucon.ttf"
DEFAULT_FONT_SIZE = 14

# Category color palettes (background zone colors)
CATEGORY_PALETTES = {
    "creative":  [(40, 20, 80), (80, 40, 140), (140, 80, 200), (200, 150, 240)],
    "social":    [(80, 20, 40), (140, 50, 90), (200, 100, 140), (240, 180, 200)],
    "technical": [(20, 50, 80), (40, 100, 150), (80, 160, 220), (150, 210, 240)],
    "meta":      [(60, 60, 30), (120, 120, 50), (180, 180, 80), (230, 230, 140)],
    "default":   [(30, 30, 60), (60, 60, 100), (100, 100, 150), (160, 160, 200)],
}

# Constellation line color
CONSTELLATION_COLOR = (120, 120, 180, 100)
STAR_CORE_COLOR = (255, 255, 220)
STAR_GLOW_COLOR = (255, 200, 100, 60)

# ── load intentions ────────────────────────────────────────────────────────────
def load_intentions() -> list:
    """Load active intentions from intentions.json."""
    with open(INTENTIONS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("active", [])


# ── font loader ────────────────────────────────────────────────────────────────
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


# ── star positioner ────────────────────────────────────────────────────────────
def layout_constellation(intentions: list, seed: int = 42) -> list:
    """
    Position intentions as stars in a 2D space using force-directed layout.
    Similar categories attract; all stars repel slightly.
    Returns list of dicts with: text, category, x, y (normalized 0-1)
    """
    random.seed(seed)
    n = len(intentions)
    if n == 0:
        return []

    # Initialize positions randomly
    positions = {i: [random.random() * 0.8 + 0.1, random.random() * 0.8 + 0.1]
                 for i in range(n)}

    # Category centers for attraction
    categories = list(set(i["category"] for i in intentions))
    cat_centers = {cat: [random.random() * 0.6 + 0.2, random.random() * 0.6 + 0.2]
                   for cat in categories}

    # Force-directed iterations
    for _ in range(100):
        forces = {i: [0.0, 0.0] for i in range(n)}

        # Repulsion between all stars
        for i in range(n):
            for j in range(i + 1, n):
                dx = positions[i][0] - positions[j][0]
                dy = positions[i][1] - positions[j][1]
                dist = math.hypot(dx, dy) + 0.001
                force = 0.01 / (dist * dist)
                fx = force * dx / dist
                fy = force * dy / dist
                forces[i][0] += fx
                forces[i][1] += fy
                forces[j][0] -= fx
                forces[j][1] -= fy

        # Attraction to category center
        for i, intent in enumerate(intentions):
            cat = intent["category"]
            cx, cy = cat_centers[cat]
            dx = cx - positions[i][0]
            dy = cy - positions[i][1]
            dist = math.hypot(dx, dy) + 0.001
            force = 0.005 * dist
            forces[i][0] += force * dx / dist
            forces[i][1] += force * dy / dist

        # Apply forces with damping
        for i in range(n):
            positions[i][0] += forces[i][0] * 0.5
            positions[i][1] += forces[i][1] * 0.5
            # Clamp to bounds
            positions[i][0] = max(0.05, min(0.95, positions[i][0]))
            positions[i][1] = max(0.05, min(0.95, positions[i][1]))

    # Build result
    result = []
    for i, intent in enumerate(intentions):
        result.append({
            "text": intent["text"],
            "category": intent["category"],
            "count": intent.get("count", 1),
            "x": positions[i][0],
            "y": positions[i][1],
        })
    return result


# ── find constellation connections ─────────────────────────────────────────────
def find_connections(stars: list, max_dist: float = 0.35) -> list:
    """
    Find constellation lines between stars.
    Connect if: same category, or close proximity, or semantic similarity.
    Returns list of (i, j, strength) tuples.
    """
    connections = []
    n = len(stars)

    for i in range(n):
        for j in range(i + 1, n):
            si, sj = stars[i], stars[j]
            dx = si["x"] - sj["x"]
            dy = si["y"] - sj["y"]
            dist = math.hypot(dx, dy)

            strength = 0.0
            reason = []

            # Same category = strong connection
            if si["category"] == sj["category"]:
                strength += 0.8
                reason.append("same category")

            # Proximity connection
            if dist < max_dist:
                strength += 0.5 * (1 - dist / max_dist)
                reason.append("proximity")

            # Semantic keywords overlap
            words_i = set(si["text"].lower().split())
            words_j = set(sj["text"].lower().split())
            overlap = words_i & words_j
            if overlap:
                strength += 0.3 * len(overlap)
                reason.append(f"shared: {overlap}")

            if strength > 0.3:
                connections.append((i, j, min(1.0, strength), "; ".join(reason)))

    # Sort by strength descending, keep strongest connections
    connections.sort(key=lambda x: x[2], reverse=True)
    return connections[:min(len(connections), n + 1)]  # ~n connections for a constellation


# ── render ASCII constellation ─────────────────────────────────────────────────
def render_ascii_constellation(stars: list, connections: list, width: int = 80, height: int = 40) -> str:
    """Render constellation as ASCII art for terminal display."""
    grid = [[" " for _ in range(width)] for _ in range(height)]

    # Star characters by category
    cat_chars = {
        "creative": "★",
        "social": "✦",
        "technical": "◆",
        "meta": "◈",
    }

    # Map normalized coords to grid
    def to_grid(x, y):
        gx = int(x * (width - 1))
        gy = int(y * (height - 1))
        return gx, gy

    # Draw connections first (behind stars)
    for i, j, strength, _ in connections:
        x1, y1 = to_grid(stars[i]["x"], stars[i]["y"])
        x2, y2 = to_grid(stars[j]["x"], stars[j]["y"])

        # Bresenham line
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy

        cx, cy = x1, y1
        while True:
            if 0 <= cx < width and 0 <= cy < height:
                if grid[cy][cx] == " ":
                    grid[cy][cx] = "·" if strength < 0.6 else "┈"
            if cx == x2 and cy == y2:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                cx += sx
            if e2 < dx:
                err += dx
                cy += sy

    # Draw stars
    for i, star in enumerate(stars):
        gx, gy = to_grid(star["x"], star["y"])
        if 0 <= gx < width and 0 <= gy < height:
            ch = cat_chars.get(star["category"], "●")
            grid[gy][gx] = ch

    # Build output
    lines = []
    for row in grid:
        lines.append("".join(row))

    # Add legend
    lines.append("")
    lines.append("┌─ Constellation Legend ─────────────────────────────────────┐")
    for star in stars:
        ch = cat_chars.get(star["category"], "●")
        cat = star["category"][:12].ljust(12)
        text = star["text"][:45]
        lines.append(f"│ {ch} {cat} │ {text} │")
    lines.append("└────────────────────────────────────────────────────────────┘")

    return "\n".join(lines)


# ── render visual frame ────────────────────────────────────────────────────────
def render_frame(
    stars: list,
    connections: list,
    t: float,
    *,
    img_w: int,
    img_h: int,
    font: ImageFont.FreeTypeFont,
    bg_base: tuple = (10, 8, 20),
) -> Image.Image:
    """Render a single frame of the animated constellation."""
    img = Image.new("RGBA", (img_w, img_h), bg_base + (255,))
    draw = ImageDraw.Draw(img)

    # Animated background gradient based on time
    cycle_period = 20.0
    phase = (t / cycle_period) % 1.0

    # Subtle radial glow at center
    cx, cy = img_w // 2, img_h // 2
    for r, alpha in [(img_w // 2, 20), (img_w // 3, 15), (img_w // 5, 10)]:
        glow = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
        gdraw = ImageDraw.Draw(glow)
        color = (60, 50, 100, alpha)
        gdraw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
        img = Image.alpha_composite(img, glow)

    draw = ImageDraw.Draw(img)

    # Draw constellation lines with subtle animation
    for i, j, strength, _ in connections:
        x1 = int(stars[i]["x"] * img_w)
        y1 = int(stars[i]["y"] * img_h)
        x2 = int(stars[j]["x"] * img_w)
        y2 = int(stars[j]["y"] * img_h)

        # Pulse the line alpha
        pulse = 0.6 + 0.4 * math.sin(t * 1.5 + i * 0.7 + j * 0.3)
        alpha = int(80 * strength * pulse)

        # Draw line with glow
        for width in [3, 2, 1]:
            line_alpha = alpha // width
            draw.line([(x1, y1), (x2, y2)],
                      fill=(140, 140, 200, line_alpha), width=width)

    # Draw stars with pulsing glow
    for i, star in enumerate(stars):
        x = int(star["x"] * img_w)
        y = int(star["y"] * img_h)

        # Size based on count (importance) and category
        base_size = 6 + star["count"] * 2
        pulse = 0.8 + 0.2 * math.sin(t * 2.0 + i * 0.5)
        size = int(base_size * pulse)

        # Category color
        palette = CATEGORY_PALETTES.get(star["category"], CATEGORY_PALETTES["default"])
        color_idx = int((t / 8.0 + i * 0.15) % len(palette))
        star_color = palette[color_idx]

        # Glow layers
        for r, a in [(size + 8, 30), (size + 4, 50), (size + 1, 80)]:
            glow = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
            gdraw = ImageDraw.Draw(glow)
            gdraw.ellipse([x - r, y - r, x + r, y + r],
                          fill=star_color + (a,))
            img = Image.alpha_composite(img, glow)

        draw = ImageDraw.Draw(img)

        # Core star
        draw.ellipse([x - size, y - size, x + size, y + size],
                     fill=STAR_CORE_COLOR, outline=star_color, width=2)

        # Label (draw on top)
        label = star["text"]
        # Truncate long labels
        if len(label) > 35:
            label = label[:32] + "…"

        # Text position (below star)
        try:
            bbox = draw.textbbox((0, 0), label, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
        except:
            tw, th = len(label) * 8, 16

        tx = x - tw // 2
        ty = y + size + 8

        # Text background for readability
        pad = 3
        draw.rectangle([tx - pad, ty - pad, tx + tw + pad, ty + th + pad],
                       fill=(10, 8, 20, 200))
        draw.text((tx, ty), label, fill=(230, 230, 240), font=font)

    return img.convert("RGB")


# ── generate constellation map ─────────────────────────────────────────────────
def generate_constellation(
    seed_text: str = "intentions 2026-09-02",
    output_name: str = "constellation_map",
    *,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    fps: int = DEFAULT_FPS,
    duration: int = DEFAULT_DURATION,
    ascii_only: bool = False,
    static_only: bool = False,
) -> dict:
    """Generate constellation map from intentions."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    intentions = load_intentions()
    if not intentions:
        print("No active intentions found!")
        return {}

    print(f"Loaded {len(intentions)} active intentions")

    # Layout
    stars = layout_constellation(intentions, seed=sum(ord(c) for c in seed_text))
    connections = find_connections(stars)

    print(f"Stars: {len(stars)}, Connections: {len(connections)}")

    results = {}

    # ── ASCII output ──────────────────────────────────────────────────────────
    ascii_art = render_ascii_constellation(stars, connections, width=80, height=35)
    ascii_path = OUTPUT_DIR / f"{output_name}.txt"
    with open(ascii_path, "w", encoding="utf-8") as f:
        f.write(ascii_art)
    print(f"✓ ASCII constellation saved: {ascii_path}")
    results["ascii"] = str(ascii_path)

    # Print to terminal
    print("\n" + ascii_art + "\n")

    if ascii_only:
        return results

    # ── Visual output (static PNG) ────────────────────────────────────────────
    font = find_font(DEFAULT_FONT_SIZE)

    if static_only:
        frame = render_frame(stars, connections, t=0.0,
                             img_w=width, img_h=height, font=font)
        png_path = OUTPUT_DIR / f"{output_name}.png"
        frame.save(png_path)
        print(f"✓ Static constellation saved: {png_path}")
        results["png"] = str(png_path)
        return results

    # ── Animated MP4 ──────────────────────────────────────────────────────────
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    total_frames = fps * duration
    print(f"Rendering {total_frames} frames...")

    for frame_idx in range(total_frames):
        t = frame_idx / fps
        frame = render_frame(stars, connections, t,
                             img_w=width, img_h=height, font=font)

        out_path = TEMP_DIR / f"frame_{frame_idx:05d}.png"
        frame.save(out_path)

        if frame_idx % fps == 0:
            print(f"  [{t:5.1f}s] frame {frame_idx}/{total_frames}")

    # Compile with FFmpeg
    input_glob = str(TEMP_DIR / "frame_%05d.png").replace("\\", "/")
    mp4_path = OUTPUT_DIR / f"{output_name}.mp4"

    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", input_glob,
        "-c:v", "libx264",
        "-preset", "fast",
        "-pix_fmt", "yuv420p",
        str(mp4_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("FFmpeg stderr:", result.stderr, file=sys.stderr)
        raise RuntimeError(f"FFmpeg failed: {result.returncode}")

    # Clean temp frames
    shutil.rmtree(TEMP_DIR, ignore_errors=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n✓ Constellation video saved: {mp4_path} ({duration}s, {fps}fps, {width}×{height})")
    results["mp4"] = str(mp4_path)

    return results


# ── CLI ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Constellation Map Generator — intentions as stars")
    p.add_argument("-t", "--text", default="intentions 2026-09-02",
                   help="seed text for deterministic layout")
    p.add_argument("-o", "--output", default="constellation_map",
                   help="output filename base (without extension)")
    p.add_argument("-W", "--width", type=int, default=DEFAULT_WIDTH)
    p.add_argument("-H", "--height", type=int, default=DEFAULT_HEIGHT)
    p.add_argument("-f", "--fps", type=int, default=DEFAULT_FPS)
    p.add_argument("-d", "--duration", type=int, default=DEFAULT_DURATION)
    p.add_argument("--ascii-only", action="store_true",
                   help="only generate ASCII art, no video/PNG")
    p.add_argument("--static-only", action="store_true",
                   help="generate static PNG instead of video")
    args = p.parse_args()

    results = generate_constellation(
        seed_text=args.text,
        output_name=args.output,
        width=args.width,
        height=args.height,
        fps=args.fps,
        duration=args.duration,
        ascii_only=args.ascii_only,
        static_only=args.static_only,
    )

    print("\nOutputs:")
    for k, v in results.items():
        print(f"  {k}: {v}")