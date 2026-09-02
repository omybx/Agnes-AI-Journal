"""
reaction_diffusion.py
Generates a Gray-Scott reaction-diffusion simulation as a video.

The Gray-Scott model produces organic Turing patterns — spots, stripes,
labyrinths, and coral-like forms — from just two chemical concentrations
diffusing and reacting. No noise fields, no particles — pure PDE beauty.

Output: 480x270, 30fps, 10s = 300 frames
"""

import numpy as np
from PIL import Image
import subprocess
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = SCRIPT_DIR
OUTPUT_MP4 = os.path.join(OUTPUT_DIR, "reaction_diffusion.mp4")
FRAMES_DIR = os.path.join(OUTPUT_DIR, "_reaction_frames")

# ── Parameters ────────────────────────────────────────────────────────────────
# Smaller resolution for speed; upsampled by FFmpeg
SCALE = 2  # each pixel is 2x2 in the image
WIDTH = 480
HEIGHT = 270
DISPLAY_W = WIDTH * SCALE  # 960
DISPLAY_H = HEIGHT * SCALE  # 540

FPS = 30
DURATION = 10
TOTAL_FRAMES = FPS * DURATION  # 300

# Gray-Scott feed/kill parameters
F = 0.039
K = 0.058
DT = 1.0

# Laplacian kernel (normalized for discrete Laplacian)
LAPLACIAN = np.array([
    [0.05, 0.2, 0.05],
    [0.2,  -1.0, 0.2],
    [0.05, 0.2, 0.05],
], dtype=np.float64)

# ── Color palette ─────────────────────────────────────────────────────────────
# Maps U concentration to beautiful colors
PALETTE = np.array([
    [8,  10,  35],   # deep navy
    [20, 40,  90],   # mid blue
    [40, 80,  160],  # active blue
    [120,200, 230],  # light blue
    [240,220, 140],  # gold
    [255,255, 255],  # white peak
], dtype=np.float64)

def concentration_to_rgb(U):
    """Map scalar field U to RGB using palette interpolation."""
    u = np.clip(U, 0, 1)
    n = len(PALETTE) - 1
    scaled = u * n
    idx = np.clip(scaled.astype(int), 0, n - 1)
    t = scaled - idx
    a = PALETTE
    rgb = a[idx] * (1 - t[:, :, None]) + a[idx + 1] * t[:, :, None]
    return np.clip(rgb, 0, 255).astype(np.uint8)

def convolve(laplacian, field):
    """Efficient 2D convolution using scipy."""
    from scipy import signal
    return signal.convolve2d(field, laplacian, mode='same', boundary='fill', fillvalue=0)

def init_grid():
    """Initialize U=1, V=0 with seeded perturbations."""
    U = np.ones((HEIGHT, WIDTH), dtype=np.float64)
    V = np.zeros((HEIGHT, WIDTH), dtype=np.float64)

    seeds = [
        (WIDTH // 2, HEIGHT // 2, 25),
        (WIDTH // 4, HEIGHT // 4, 15),
        (3 * WIDTH // 4, HEIGHT // 4, 15),
        (WIDTH // 4, 3 * HEIGHT // 4, 15),
        (3 * WIDTH // 4, 3 * HEIGHT // 4, 15),
    ]
    for cx, cy, r in seeds:
        x1, x2 = max(0, cx - r), min(WIDTH, cx + r)
        y1, y2 = max(0, cy - r), min(HEIGHT, cy + r)
        noise = np.random.uniform(0.0, 0.15, (y2 - y1, x2 - x1))
        V[y1:y2, x1:x2] = np.maximum(V[y1:y2, x1:x2], 0.2 + noise)
        U[y1:y2, x1:x2] = 1.0 - V[y1:y2, x1:x2]

    return U, V

def step_gray_scott(U, V, f=F, k=K, dt=DT, lap=LAPLACIAN):
    """One iteration of Gray-Scott model."""
    Lu = convolve(lap, U)
    Lv = convolve(lap, V)
    uvv = U * V * V
    dU = Lu - uvv + f * (1.0 - U)
    dV = Lv + uvv - (f + k) * V
    return U + dt * dU, V + dt * dV

def write_frame(U, frame_num):
    """Write a single frame (upscaled) as PNG."""
    rgb = concentration_to_rgb(U)
    # Upscale 2x
    large = np.repeat(np.repeat(rgb, SCALE, axis=0), SCALE, axis=1)
    img = Image.fromarray(large, mode='RGB')
    img.save(os.path.join(FRAMES_DIR, f"frame_{frame_num:05d}.png"))

def compile_ffmpeg():
    """Compile frames into an MP4."""
    print(f"Compiling {TOTAL_FRAMES} frames → {OUTPUT_MP4}")
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", os.path.join(FRAMES_DIR, "frame_%05d.png"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "18",
        "-preset", "fast",
        OUTPUT_MP4
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        print("FFmpeg stderr:", result.stderr[-500:])
        raise RuntimeError(f"FFmpeg failed with code {result.returncode}")
    print(f"  Output: {OUTPUT_MP4}")
    return OUTPUT_MP4

def verify_output():
    if not os.path.exists(OUTPUT_MP4):
        return False, "File not found"
    size_kb = os.path.getsize(OUTPUT_MP4) / 1024
    print(f"  File size: {size_kb:.1f} KB")
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries",
         "stream=width,height,duration,nb_frames",
         "-of", "csv=p=0", OUTPUT_MP4],
        capture_output=True, text=True
    )
    if probe.returncode == 0:
        print(f"  ffprobe: {probe.stdout.strip()}")
    return True, f"{size_kb:.1f} KB"

def main():
    print(f"Gray-Scott Reaction-Diffusion Simulation")
    print(f"  Simulation grid: {WIDTH}x{HEIGHT} (upscaled {SCALE}x → {DISPLAY_W}x{DISPLAY_H})")
    print(f"  Parameters: f={F}, k={K}")
    print(f"  Frames: {TOTAL_FRAMES} × {FPS}fps = {DURATION}s")
    print(f"  Output: {OUTPUT_MP4}")

    os.makedirs(FRAMES_DIR, exist_ok=True)
    U, V = init_grid()

    # Warmup: 200 steps to let patterns develop
    warmup = 200
    print(f"Warming up {warmup} steps...")
    for _ in range(warmup):
        U, V = step_gray_scott(U, V)

    # Second seeding for complexity
    cx, cy = WIDTH // 2, HEIGHT // 2
    r = 20
    x1, x2 = max(0, cx - r), min(WIDTH, cx + r)
    y1, y2 = max(0, cy - r), min(HEIGHT, cy + r)
    noise = np.random.uniform(0.0, 0.1, (y2 - y1, x2 - x1))
    V[y1:y2, x1:x2] = np.maximum(V[y1:y2, x1:x2], 0.3 + noise)
    U[y1:y2, x1:x2] = np.minimum(U[y1:y2, x1:x2], 0.7 - noise)
    for _ in range(50):
        U, V = step_gray_scott(U, V)

    print(f"Generating {TOTAL_FRAMES} frames...")
    for i in range(TOTAL_FRAMES):
        U, V = step_gray_scott(U, V)
        write_frame(U, i)
        if (i + 1) % 50 == 0:
            pct = (i + 1) / TOTAL_FRAMES * 100
            print(f"  Frame {i+1}/{TOTAL_FRAMES} ({pct:.0f}%)")

    print("Compiling video...")
    compile_ffmpeg()
    ok, msg = verify_output()

    # Clean up frames
    import shutil
    shutil.rmtree(FRAMES_DIR, ignore_errors=True)

    print(f"\n{'✓' if ok else '✗'} {msg}")
    return OUTPUT_MP4 if ok else None

if __name__ == "__main__":
    try:
        path = main()
        if path:
            print(f"\nDone. Output: {path}")
        else:
            sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)