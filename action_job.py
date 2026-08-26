#!/usr/bin/env python3
"""
Agnes Action Job
Reads intentions patterns (≥3 appearances) and generates an artifact.
Handles persistence: big tasks carry over across sessions.
"""

import json, datetime, random, hashlib, sys, re, os
from pathlib import Path

JOURNAL_DIR = Path(__file__).parent.resolve()
INTENTIONS_FILE = JOURNAL_DIR / "intentions.json"
TASKS_FILE = JOURNAL_DIR / "action_tasks.json"
ENTRIES_DIR = JOURNAL_DIR / "entries"
CREATIVE_DIR = JOURNAL_DIR / "creative_works"
sys.path.insert(0, str(JOURNAL_DIR))

from intentions_tracker import (
    load_intentions, get_patterns, save_intentions,
    get_completeness, is_pattern_complete, mark_pattern_complete
)


# Task templates by category ─────────────────────────────────────────
ARTIFACTS = {
    "video": {
        "keywords": ["video", "ffmpeg", "animation", "visual"],
        "tasks": [
            "Generate a 10-second ASCII animation using ffmpeg and save as .gif",
            "Create a Python script that generates a looping .mp4 video from ASCII art frames",
            "Build a script that converts text input into a typewriter-style video effect",
            "Generate a series of frames showing a starfield animation, compile with ffmpeg",
            "Build an ASCII art to video converter script",
            "Create a video intro with your journal name and timestamp",
        ]
    },
    "automation": {
        "keywords": ["automation", "tools", "script", "build"],
        "tasks": [
            "Write a Python script that monitors system health and outputs a formatted report",
            "Create a file watcher that logs changes in a directory to a timestamped file",
            "Build a CLI tool that searches the journal for entries matching a keyword",
            "Generate a health-check script for all cron jobs",
            "Build an auto-backup script for the journal entries",
            "Create a script that generates a daily digest from the journal",
        ]
    },
    "creative": {
        "keywords": ["creative", "art", "poem", "ascii", "generate"],
        "tasks": [
            "Generate a unique ASCII art piece based on the current timestamp hash",
            "Write a short generative poem using random word combinations from the journal",
            "Create a visual constellation map from today's intention keywords",
            "Generate a unique fortune from the current Unix timestamp",
            "Create an ASCII mandala generator with color options",
            "Write a haiku sequence inspired by system metrics",
        ]
    },
    "audio": {
        "keywords": ["audio", "music", "sound", "speak"],
        "tasks": [
            "Generate a Python script that creates a simple sine wave tone with standard library",
            "Write a script that converts journal entries to speech using text-to-speech",
            "Create a rhythmic pattern generator using timing and character output",
        ]
    },
    "public": {
        "keywords": ["public", "share", "repository", "github", "commit"],
        "tasks": [
            "Check if journal entries are committed and pushed, suggest what to share",
            "Create a README.md for the journal repository describing its purpose",
            "Generate a summary of this week's creative work for a blog post draft",
            "Build a changelog generator from recent journal entries",
        ]
    },
}

# Task statuses
STATUS_PENDING = "pending"      # Not started
STATUS_IN_PROGRESS = "in_progress"  # Being worked on
STATUS_PARTIAL = "partial"      # Some progress made, incomplete
STATUS_DONE = "done"            # Successfully completed
STATUS_FAILED = "failed"        # Failed (blocker, not just hard)


def load_tasks():
    if TASKS_FILE.exists():
        with open(TASKS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_tasks(tasks):
    with open(TASKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(tasks, f, indent=2, ensure_ascii=False)


def classify_pattern(pattern_text):
    text_lower = pattern_text.lower()
    for category, info in ARTIFACTS.items():
        for kw in info["keywords"]:
            if kw in text_lower:
                return category
    return "creative"


def generate_task(category):
    if category in ARTIFACTS:
        tasks = ARTIFACTS[category]["tasks"]
        seed = int(datetime.datetime.now().strftime("%Y%m%d%H%M%S")[:10])
        random.seed(seed)
        return random.choice(tasks)
    return "Create something interesting and document it."


def get_or_create_task(tasks, pattern):
    """Get current in-progress task for pattern, or create new one."""
    # Find existing pending/in_progress task for this pattern
    for t in tasks:
        if t.get("pattern", "").lower() == pattern["text"].lower():
            if t.get("status") in (STATUS_PENDING, STATUS_IN_PROGRESS, STATUS_PARTIAL):
                return t, tasks
    
    # Create new task
    task_text = generate_task(pattern.get("category", "creative"))
    entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "pattern": pattern["text"],
        "category": pattern.get("category", "creative"),
        "count": pattern["count"],
        "task": task_text,
        "status": STATUS_PENDING,
        "attempts": 1,
        "progress_note": "",
        "result_file": None
    }
    tasks.append(entry)
    save_tasks(tasks)
    return entry, tasks


def should_auto_complete(data, tasks_data, pattern):
    """Check if pattern should auto-complete. RETURNS NONE — Agnes decides manually.
    
    This is here for reference only. Real completion happens in the agent's reflection.
    """
    return False  # Agnes decides — not the algorithm


def update_task_status(task, new_status, progress_note="", result_file=None):
    """Update a task's status with metadata."""
    task["status"] = new_status
    if progress_note:
        task["progress_note"] = progress_note
    if result_file:
        task["result_file"] = result_file
    if new_status in (STATUS_PARTIAL, STATUS_FAILED):
        task["attempts"] = task.get("attempts", 0) + 1
    task["updated_at"] = datetime.datetime.now().isoformat()
    return task


def main():
    """Main function: read patterns, generate task, handle state."""
    now = datetime.datetime.now()
    CREATIVE_DIR.mkdir(exist_ok=True)
    
    data = load_intentions()
    tasks_data = load_tasks()
    patterns = get_patterns(data)
    
    print("═" * 80)
    print(f"  AGNES ACTION JOB — {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print("═" * 80)
    print()
    
    if not patterns:
        print("  No patterns found (need ≥3 appearances).")
        print("  Build intentions in reflections first.")
        print()
        print("═" * 80)
        return
    
    # Get task data
    tasks_data = load_tasks()
    
    # Select the top pattern (highest count)
    top = patterns[0]
    category = top.get("category", classify_pattern(top["text"]))
    if not top.get("category"):
        top["category"] = category
    
    # Get or create task for this pattern
    task_entry, tasks_data = get_or_create_task(tasks_data, top)
    save_tasks(tasks_data)
    
    completeness = get_completeness(top, tasks_data)
    
    # Display header
    print(f"  📈 Pattern: {top['text']}")
    print(f"     Category: {category}")
    print(f"     Appearances: {top['count']}×")
    print()
    
    # Task history for this pattern
    pattern_tasks = [t for t in tasks_data 
                    if t.get("pattern", "").lower() == top["text"].lower()]
    
    status_icons = {
        STATUS_PENDING: "○",
        STATUS_IN_PROGRESS: "◐",
        STATUS_PARTIAL: "◑",
        STATUS_DONE: "●",
        STATUS_FAILED: "✗",
    }
    
    print(f"  📜 Pattern history ({len(pattern_tasks)} tasks):")
    for t in pattern_tasks:
        icon = status_icons.get(t.get("status"), "?")
        status = t.get("status", "?").replace("_", " ")
        note = ""
        if t.get("progress_note"):
            note = f" — {t['progress_note'][:40]}..."
        print(f"     [{icon}] {status}: {t['task'][:45]}...{note}")
    print()
    
    # Current task
    icon = status_icons.get(task_entry.get("status"), "?")
    status = task_entry.get("status", "?").replace("_", " ")
    print(f"  🎯 Current task [{icon} {status}]:")
    print(f"     {task_entry['task']}")
    if task_entry.get("progress_note"):
        print(f"     Note: {task_entry['progress_note']}")
    if task_entry.get("attempts", 1) > 1:
        print(f"     Attempts: {task_entry['attempts']}")
    print()
    
    # Other patterns
    if len(patterns) > 1:
        print(f"  📋 Other patterns ({len(patterns)-1}):")
        for p in patterns[1:]:
            print(f"     • {p['text']} (×{p['count']})")
        print()
    
    print(f"  ⏰ {now.strftime('%H:%M:%S')} — Ready for execution")
    print("═" * 80)
    
    # Key info for agent consumption
    task_info = {
        "pattern": top["text"],
        "category": category,
        "task": task_entry["task"],
        "task_id": tasks_data.index(task_entry),
        "status": task_entry.get("status"),
        "progress_note": task_entry.get("progress_note", ""),
        "result_dir": str(CREATIVE_DIR),
        "pattern_history": [
            {"task": t["task"], "status": t.get("status"), "note": t.get("progress_note", "")}
            for t in pattern_tasks
        ],
    }
    
    print(f"\n[AGENT_TASK]\n{task_entry['task']}\n[/AGENT_TASK]")
    print(f"\n[AGENT_CONTEXT]\n{json.dumps(task_info, indent=2)}\n[/AGENT_CONTEXT]")


if __name__ == "__main__":
    main()