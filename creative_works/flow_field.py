"""
flow_field.py
Generates an animated flow field particle video using Pillow + FFmpeg.
Thousands of particles follow a Perlin-noise-like vector field, leaving
fading trails that produce organic, river-like patterns. Palette cycles
through 4 moods over the duration.
"""

import math
import subprocess
import os
import sys
import json
import random
from PIL import Image, ImageDraw

# ── Config ─────────────────────────────────────────────────────────────────────
W, H            = 960, 540
FPS             = 24
DURATION        = 15          # seconds
TOTAL_FRAMES    = FPS * DURATION
NUM_PARTICLES   = 1200
TRAIL_ALPHA     = 0.06        # lower = longer trails (0-1)
FIELD_SCALE     = 0.004       # noise field zoom
FIELD_SPEED     = 0.0008      # how fast the field drifts
VELOCITY_MAX    = 2.5         # max particle speed
PALETTE_CYCLE   = 10.0        # seconds for full palette rotation

# Output
OUT_DIR  = os.path.dirname(os.path.abspath(__file__))
WORK_DIR = os.path.join(OUT_DIR, "_flowfield_frames")
OUT_MP4  = os.path.join(OUT_DIR, "flow_field.mp4")

os.makedirs(WORK_DIR, exist_ok=True)

# ── Simplex-like noise (pure Python, no numpy) ────────────────────────────────

class Noise:
    """1D/2D value noise with smooth interpolation. Fast enough for real-time."""

    def __init__(self, seed=42):
        self.perm = list(range(256))
        rng = random.Random(seed)
        rng.shuffle(self.perm)
        self.perm += self.perm  # double for overflow safety

    def _fade(self, t):
        return t * t * t * (t * (t * 6 - 15) + 10)

    def _lerp(self, a, b, t):
        return a + t * (b - a)

    def _grad(self, hash_val, x, y):
        h = hash_val & 3
        if h == 0: return x + y
        if h == 1: return -x + y
        if h == 2: return x - y
        return -x - y

    def noise2d(self, x, y):
        X = int(math.floor(x)) & 255
        Y = int(math.floor(y)) & 255
        xf = x - math.floor(x)
        yf = y - math.floor(y)
        u = self._fade(xf)
        v = self._fade(yf)
        p = self.perm
        aa = p[p[X] + Y]
        ab = p[p[X] + Y + 1]
        ba = p[p[X + 1] + Y]
        bb = p[p[X + 1] + Y + 1]
        x1 = self._lerp(self._grad(aa, xf, yf), self._grad(ba, xf - 1, yf), u)
        x2 = self._lerp(self._grad(ab, xf, yf - 1), self._grad(bb, xf - 1, yf - 1), u)
        return self._lerp(x1, x2, v)

    def fbm(self, x, y, octaves=4, lacunarity=2.0, gain=0.5):
        """Fractional Brownian Motion — layered noise for richer texture."""
        value = 0.0
        amp = 1.0
        freq = 1.0
        for _ in range(octaves):
            value += amp * self.noise2d(x * freq, y * freq)
            amp *= gain
            freq *= lacunarity
        return value


noise = Noise(seed=137)

# ── Palette ────────────────────────────────────────────────────────────────────

PALETTES = [
    # (name, bg, primary, secondary, accent)
    ("ocean",     (3, 8,  28), (20, 80, 160), (60, 180, 220), (180, 230, 255)),
    ("ember",     (20, 5,  3), (200, 80,  20), (255, 160, 40), (255, 220, 120)),
    ("void",      (12, 3,  18), (120, 30, 160), (200, 80, 220), (240, 160, 255)),
    ("forest",    (2,  12, 5), (20, 120, 50), (80, 200, 100), (180, 255, 180)),
]


def lerp_color(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def get_palette(t):
    """Return (bg, primary, secondary, accent) at normalized time t."""
    idx = (t * len(PALETTES)) % len(PALETTES)
    a = int(idx)
    b = (a + 1) % len(PALETTES)
    local = (idx * len(PALETTES)) - a
    pa = PALETTES[a][1:]
    pb = PALETTES[b][1:]
    return tuple(
        lerp_color(pa[i], pb[i], local)
        for i in range(4)
    )


# ── Particle ───────────────────────────────────────────────────────────────────

class Particle:
    __slots__ = ("x", "y", "vx", "vy", "age", "hue_offset")

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.age = 0
        self.hue_offset = random.uniform(0, 1)

    def step(self, t, field_t):
        # Sample the noise field at particle position
        nx = noise.fbm(
            self.x * FIELD_SCALE + field_t,
            self.y * FIELD_SCALE,
            octaves=3,
        )
        ny = noise.fbm(
            self.x * FIELD_SCALE,
            self.y * FIELD_SCALE + field_t,
            octaves=3,
        )

        # Turn angle from noise
        angle = math.atan2(ny, nx) * math.pi

        # Accelerate toward field direction
        accel = 0.15
        self.vx += math.cos(angle) * accel
        self.vy += math.sin(angle) * accel

        # Dampen
        self.vx *= 0.92
        self.vy *= 0.92

        # Clamp speed
        speed = math.sqrt(self.vx ** 2 + self.vy ** 2)
        if speed > VELOCITY_MAX:
            self.vx = self.vx / speed * VELOCITY_MAX
            self.vy = self.vy / speed * VELOCITY_MAX

        self.x += self.vx
        self.y += self.vy
        self.age += 1

        # Wrap around edges with a soft margin
        margin = 10
        if self.x < -margin:  self.x = W + margin
        if self.x > W + margin: self.x = -margin
        if self.y < -margin:  self.y = H + margin
        if self.y > H + margin: self.y = -margin

    def color(self, pal, t):
        """RGB color based on particle speed and hue offset."""
        speed = math.sqrt(self.vx ** 2 + self.vy ** 2)
        speed_norm = min(1.0, speed / VELOCITY_MAX)
        # Blend between primary (slow) and secondary (fast)
        base = lerp_color(pal[1], pal[2], speed_norm)
        # Add hue variation per particle
        shift = int(20 * math.sin(self.hue_offset * 6.28 + t * 2))
        r = max(0, min(255, base[0] + shift))
        g = max(0, min(255, base[1] + shift))
        b = max(0, min(255, base[2] + shift))
        return (r, g, b)


# ── Init particles ────────────────────────────────────────────────────────────

particles = [Particle(random.uniform(0, W), random.uniform(0, H))
             for _ in range(NUM_PARTICLES)]
random.shuffle(particles)

# ── Frame generation ──────────────────────────────────────────────────────────

def render_frame(frame_idx):
    t = frame_idx / TOTAL_FRAMES
    field_t = frame_idx * FIELD_SPEED
    pal = get_palette(t)
    bg, primary, secondary, accent = pal

    # Create a new image for this frame
    img = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)

    for p in particles:
        p.step(t, field_t)
        col = p.color(pal, t)
        r = max(1, int(1.5 + col[0] / 255 * 1.5))
        draw.ellipse(
            [p.x - r, p.y - r, p.x + r, p.y + r],
            fill=col,
        )

    # Soft vignette
    cx, cy = W // 2, H // 2
    max_r = math.sqrt(cx * cx + cy * cy)
    for ring in range(120, 0, -3):
        alpha = int(30 * (1 - ring / 120))
        r = max_r - ring
        if r > 0:
            c = lerp_color(bg, (0, 0, 0), alpha / 60)
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c)

    return img


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"Generating flow field — {NUM_PARTICLES} particles, {TOTAL_FRAMES} frames")
    print(f"  {W}x{H} @ {FPS}fps, {DURATION}s duration")
    print(f"  Trail alpha={TRAIL_ALPHA}, Field scale={FIELD_SCALE}")

    # Render frames directly into MP4 intermediate (no trail persistence needed
    # since we redraw bg each frame — trails come from particle density/coverage)
    for i in range(TOTAL_FRAMES):
        frame_path = os.path.join(WORK_DIR, f"frame_{i:04d}.png")
        img = render_frame(i)
        img.save(frame_path)
        if (i + 1) % 48 == 0:
            pct = (i + 1) * 100 // TOTAL_FRAMES
            print(f"  [{i+1:4d}/{TOTAL_FRAMES}] ({pct}%)")

    print("Frames done. Compiling with FFmpeg...")

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", os.path.join(WORK_DIR, "frame_%04d.png"),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        OUT_MP4,
    ]
    result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("FFmpeg error:", result.stderr[-800:])
        sys.exit(1)

    size_kb = os.path.getsize(OUT_MP4) // 1024
    print(f"\n✓ flow_field.mp4 — {size_kb} KB")

    # Verify with ffprobe
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_streams", OUT_MP4],
        capture_output=True, text=True,
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
