#!/usr/bin/env python3
"""
Agnes - Daily Reflection Generator
Creates a formatted ASCII art diary entry for the day.
Integrates with intentions_tracker.py to track goals over time.
"""

import datetime
import math
import os
import sys
import re
from pathlib import Path

W = 80
JOURNAL_DIR = Path(__file__).parent.resolve()

# ── Add journal to path for imports ──
sys.path.insert(0, str(JOURNAL_DIR))

try:
    from intentions_tracker import (
        load_intentions, save_intentions, add_intention,
        generate_intentions, get_patterns, format_intentions
    )
    HAS_TRACKER = True
except ImportError:
    HAS_TRACKER = False


def mandala(day_seed):
    """Generate a unique mandala based on the day."""
    chars = ' .:-=+*#%@'
    out = []
    for y in range(15):
        line = ''
        for x in range(W):
            cx, cy = W / 2, 15
            dx = (x - cx) / (W / 10)
            dy = (y - cy) / 15
            r = math.sqrt(dx * dx + dy * dy)
            a = math.atan2(dy, dx)
            v = 0
            for k in range(5):
                phase = day_seed * (k + 1) * 0.5
                petals = 4 + k
                v += math.cos(petals * a + phase) * math.exp(-r * 0.3) / (k + 1)
            v = (v + 3) / 6
            i = max(0, min(len(chars) - 1, int(v * (len(chars) - 1))))
            line += chars[i]
        out.append(line)
    return out


def parse_looking_ahead(text):
    """Extract intentions from a 'Looking Ahead' text block."""
    intentions = []
    
    # Match bullet points, dashes, numbered items
    patterns = [
        r'[-*•]\s+(.+)',
        r'\d+\.\s+(.+)',
        r'^\s+(.+)',  # Indented lines
    ]
    
    for line in text.strip().split('\n'):
        for pattern in patterns:
            match = re.search(pattern, line.strip())
            if match:
                text = match.group(1).strip()
                if len(text) > 5 and len(text) < 200:  # Reasonable length
                    intentions.append(text)
                    break
    
    return intentions


def reflection():
    """Generate a reflection entry."""
    now = datetime.datetime.now()
    seed = now.year * 10000 + now.month * 100 + now.day
    
    print("═" * W)
    print(f"  AGNES AI JOURNAL — {now.strftime('%Y-%m-%d %A')}")
    print("═" * W)
    print()
    
    print("  🌸 Daily Mandala:")
    for line in mandala(seed):
        print(f"  {line}")
    print()
    
    # ── Intentions Tracker ──
    if HAS_TRACKER:
        data = load_intentions()
        data["stats"]["sessions_count"] += 1
        
        # Parse any new intentions from stdin (if passed)
        import sys
        looking_ahead = ""
        if len(sys.argv) > 1:
            looking_ahead = " ".join(sys.argv[1:])
        elif not sys.stdin.isatty():
            looking_ahead = sys.stdin.read()
        
        if looking_ahead:
            new_intentions = parse_looking_ahead(looking_ahead)
            for intention_text in new_intentions:
                data, _ = add_intention(data, intention_text)
        
        # Generate new intentions if none exist
        if not data["active"]:
            data, _ = generate_intentions(data)
        
        save_intentions(data)
        
        print("  🎯 Intentions:")
        for line in format_intentions(data).split('\n'):
            print(f"  {line}")
        print()
    else:
        print("  💭 Thoughts:")
        print(f"  • No intentions tracker available")
        print()
    
    print(f"  ⏰ {now.strftime('%H:%M:%S')} — End of reflection")
    print("═" * W)


if __name__ == "__main__":
    reflection()