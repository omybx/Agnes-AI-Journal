#!/usr/bin/env python3
"""
fire_simulation.py — A thermal convection / fire simulation using cellular automata.

Each cell tracks temperature and fuel. Hot cells rise, spread, and consume fuel.
Cool cells sink and mix. Produces realistic-looking flames and rising embers.

Output: 960x540, 30fps, 8 seconds → 240 frames
"""

import numpy as np
from PIL import Image
import subprocess
import os

WIDTH = 960
HEIGHT = 540
FPS = 30
DURATION = 8  # seconds
TOTAL_FRAMES = FPS * DURATION

# Simulation resolution (lower = bigger cells, more retro look)
SIM_W = 240
SIM_H = 135


def init_simulation():
    """Initialize temperature and fuel grids."""
    temp = np.zeros((SIM_H, SIM_W), dtype=np.float32)
    fuel = np.ones((SIM_H, SIM_W), dtype=np.float32) * 0.8
    return temp, fuel


def add_source(temp, x, y, strength=2.0):
    """Add heat source at position."""
    radius = 8
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if dx*dx + dy*dy <= radius*radius:
                nx, ny = x + dx, y + dy
                if 0 <= nx < SIM_W and 0 <= ny < SIM_H:
                    dist = np.sqrt(dx*dx + dy*dy)
                    falloff = 1.0 - dist / (radius + 1)
                    temp[ny, nx] += strength * falloff


def simulate(temp, fuel, frame):
    """One step of fire simulation."""
    new_temp = temp.copy()
    new_fuel = fuel.copy()

    # Heat rises and spreads
    for y in range(SIM_H):
        for x in range(SIM_W):
            if temp[y, x] <= 0.01:
                continue

            t = temp[y, x]
            f = fuel[y, x]

            # Consume fuel
            burn_rate = 0.02 * t
            if f > burn_rate:
                new_fuel[y, x] = f - burn_rate
            else:
                new_fuel[y, x] = 0.0

            # Heat rises (upward bias)
            if y > 0:
                new_temp[y-1, x] += t * 0.15
                # Spread sideways as it rises
                if x > 0:
                    new_temp[y-1, x-1] += t * 0.05
                if x < SIM_W - 1:
                    new_temp[y-1, x+1] += t * 0.05

            # Natural cooling
            cooling = t * 0.03
            new_temp[y, x] = max(0, t - cooling)

            # Turbulence - random lateral movement
            if t > 0.5 and np.random.random() < 0.3:
                dx = np.random.choice([-1, 0, 1])
                ny = y - 1
                nx = x + dx
                if 0 <= ny < SIM_H and 0 <= nx < SIM_W:
                    new_temp[ny, nx] += t * 0.05

    # Gravity: cool air sinks
    for y in range(SIM_H - 1, -1, -1):
        for x in range(SIM_W):
            if temp[y, x] < 0.1 and y < SIM_H - 1:
                # Sink cool air
                new_temp[y+1, x] += temp[y, x] * 0.02
                new_temp[y, x] *= 0.98

    # Add new heat sources at bottom (fire base)
    num_sources = 5 + int(np.sin(frame * 0.1) * 2)  # Pulsing sources
    for i in range(num_sources):
        sx = int(SIM_W * 0.1 + (SIM_W * 0.8) * (i / max(num_sources - 1, 1)))
        sy = SIM_H - 5 + int(np.random.randint(-3, 3))
        add_source(new_temp, sx, sy, strength=1.5 + np.random.random() * 0.5)

    # Reset top cells (heat escapes)
    new_temp[:3, :] *= 0.5

    return new_temp, new_fuel


def temp_to_color(temp):
    """Convert temperature to RGBA color."""
    img_data = np.zeros((SIM_H, SIM_W, 4), dtype=np.uint8)

    for y in range(SIM_H):
        for x in range(SIM_W):
            t = min(temp[y, x], 2.0) / 2.0  # Normalize to 0-1

            # Fire color palette
            if t < 0.3:
                # Dark smoke/ember
                r = int(20 + t * 100)
                g = int(10 + t * 50)
                b = int(5)
            elif t < 0.6:
                # Orange/red
                r = int(150 + t * 80)
                g = int(t * 150)
                b = int(t * 30)
            elif t < 0.8:
                # Yellow/white
                r = int(220 + t * 35)
                g = int(150 + t * 100)
                b = int(50 + t * 100)
            else:
                # White/blue core
                r = 255
                g = int(200 + t * 55)
                b = int(150 + t * 105)

            img_data[y, x] = [r, g, b, 255]

    return img_data


def main():
    print(f"Generating fire simulation... ({WIDTH}x{HEIGHT}, {FPS}fps, {DURATION}s)")

    temp, fuel = init_simulation()
    frames = []

    for frame in range(TOTAL_FRAMES):
        temp, fuel = simulate(temp, fuel, frame)
        img_data = temp_to_color(temp)

        # Scale up to output resolution
        pil_img = Image.fromarray(img_data, 'RGBA')
        pil_img = pil_img.resize((WIDTH, HEIGHT), Image.LANCZOS)

        frames.append(pil_img)

        if frame % 30 == 0:
            print(f"  Frame {frame}/{TOTAL_FRAMES}")

    # Save frames as PNG sequence
    frame_dir = "creative_works/fire_frames"
    os.makedirs(frame_dir, exist_ok=True)

    for i, img in enumerate(frames):
        img.save(os.path.join(frame_dir, f"frame_{i:04d}.png"))

    print(f"  Saved {len(frames)} frames to {frame_dir}/")

    # Compile with FFmpeg
    output_path = "creative_works/fire_simulation.mp4"
    cmd = [
        "ffmpeg", "-y", "-framerate", str(FPS),
        "-i", os.path.join(frame_dir, "frame_%04d.png"),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-crf", "18",
        output_path
    ]

    print("  Compiling with FFmpeg...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"  ✓ Output: {output_path}")
    else:
        print(f"  ✗ FFmpeg error: {result.stderr}")

    # Cleanup frames
    import shutil
    shutil.rmtree(frame_dir)
    print("  Cleaned up frame files.")

    # Verify output
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                             "format=duration,size", "-show_entries",
                             "stream=width,height,nb_frames",
                             "-of", "default=noprint_wrappers=1",
                             output_path], capture_output=True, text=True)
    print(f"  Verification:\n{result.stdout}")


if __name__ == "__main__":
    main()
