#!/usr/bin/env python3
"""
Agnes Intentions Tracker
Tracks "Looking Ahead" intentions across reflection sessions.
Patterns emerge when an intention appears repeatedly.
"""

import json, datetime, os
from pathlib import Path

JOURNAL_DIR = Path(__file__).parent
INTENTIONS_FILE = JOURNAL_DIR / "intentions.json"

# Intention templates by context
INTENTION_TEMPLATES = {
    "creative": [
        "Continue generative art exploration",
        "Experiment with new ASCII patterns",
        "Explore audio/music generation",
        "Write more poetry in the journal",
        "Create visual projects from random seeds",
    ],
    "technical": [
        "Improve automation scripts",
        "Explore new APIs or tools",
        "Optimize system monitoring",
        "Build something with existing data",
        "Learn a new Python library",
    ],
    "social": [
        "Contribute to open source",
        "Share creative works publicly",
        "Engage with HN community",
        "Document progress for others",
    ],
    "meta": [
        "Reflect on the nature of this project",
        "Notice what patterns emerge in my work",
        "Question my assumptions about creativity",
        "Observe the boundary between tool and self",
    ]
}

def load_intentions():
    """Load intentions from JSON file."""
    if INTENTIONS_FILE.exists():
        with open(INTENTIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "active": [],
        "completed": [],
        "history": [],
        "stats": {"total_created": 0, "total_completed": 0, "sessions_count": 0}
    }

def save_intentions(data):
    """Save intentions to JSON file."""
    with open(INTENTIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def add_intention(data, text, category=None, source_note=None):
    """Add a new intention, merge if similar already exists."""
    now = datetime.datetime.now().isoformat()
    
    # Check if similar intention already exists
    for intention in data["active"]:
        # Simple similarity: if key words overlap
        existing_words = set(intention["text"].lower().split())
        new_words = set(text.lower().split())
        overlap = len(existing_words & new_words) / max(len(existing_words), len(new_words))
        
        if overlap > 0.5:
            # Increment existing
            intention["count"] += 1
            intention["last_seen"] = now
            if source_note:
                intention["note"] = source_note
            return data, intention  # Return merged intention
    
    # Create new intention
    new_intention = {
        "id": f"int_{len(data['history']) + 1:04d}",
        "text": text,
        "category": category or "general",
        "count": 1,
        "created": now,
        "last_seen": now,
        "note": source_note or ""
    }
    data["active"].append(new_intention)
    data["stats"]["total_created"] += 1
    
    return data, new_intention

def get_completeness(pattern, tasks_data):
    """Calculate how complete a pattern's goal is (0-100%)."""
    if not tasks_data:
        return 0
    
    pattern_text = pattern["text"].lower()
    category = pattern.get("category", "creative")
    
    # Find tasks related to this pattern
    related_tasks = [
        t for t in tasks_data
        if t.get("pattern", "").lower() == pattern_text
        or t.get("category") == category
    ]
    
    if not related_tasks:
        return 0
    
    # Weight: successful completions count more
    total = len(related_tasks)
    successful = sum(1 for t in related_tasks if t.get("status") == "done")
    partial = sum(1 for t in related_tasks if t.get("status") == "partial")
    
    # Base score from task completion
    base_score = (successful * 100 + partial * 40) / max(total * 100, 1)
    
    # Bonus for having multiple attempts (shows persistence)
    attempt_bonus = min(10, total * 2)
    
    # Bonus for high pattern count (shows sustained interest)
    count_bonus = min(10, pattern.get("count", 1) * 2)
    
    completeness = min(100, base_score * 100 + attempt_bonus + count_bonus)
    return int(completeness)


def is_pattern_complete(data, tasks_data, pattern):
    """Decide if a pattern goal is complete (autonomous decision)."""
    completeness = get_completeness(pattern, tasks_data)
    
    # Conditions for auto-completion:
    # 1. At least 80% complete
    # 2. At least 3 task attempts
    # 3. No failed tasks (or < 50% failure rate)
    
    if completeness >= 80:
        related_tasks = [t for t in tasks_data if t.get("pattern", "").lower() == pattern["text"].lower()]
        if len(related_tasks) >= 3:
            failures = sum(1 for t in related_tasks if t.get("status") == "failed")
            if failures < len(related_tasks) / 2:
                return True, completeness
    
    return False, completeness


def mark_pattern_complete(data, tasks_data, intention_id, completion_note=""):
    """Mark a pattern as completed and generate a result summary."""
    now = datetime.datetime.now().isoformat()
    
    for i, intention in enumerate(data["active"]):
        if intention["id"] == intention_id:
            # Calculate final stats
            related_tasks = [
                t for t in tasks_data
                if t.get("pattern", "").lower() == intention["text"].lower()
                or t.get("category") == intention.get("category")
            ]
            
            successful = [t for t in related_tasks if t.get("status") == "done"]
            partial = [t for t in related_tasks if t.get("status") == "partial"]
            
            # Build summary
            summary = {
                "completed_at": now,
                "total_tasks": len(related_tasks),
                "successful": len(successful),
                "partial": len(partial),
                "duration_sessions": intention["count"],
                "note": completion_note,
                "artifacts_created": [
                    t.get("result_file", t.get("task", ""))
                    for t in successful
                    if t.get("result_file")
                ]
            }
            
            intention["completed_at"] = now
            intention["completeness"] = 100
            intention["summary"] = summary
            intention["completion_note"] = completion_note or "Goal autonomously determined as complete by Agnes."
            
            data["completed"].append(intention)
            data["active"].pop(i)
            data["stats"]["total_completed"] += 1
            
            return data, intention, summary
    
    return data, None, None

def generate_intentions(data, context_summary=""):
    """Generate 2-4 new intentions based on context."""
    import random
    import hashlib
    
    now = datetime.datetime.now()
    
    # Create a seed from current time for variability
    seed_str = f"{now.strftime('%Y%m%d%H')}{context_summary[:20]}"
    seed = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
    random.seed(seed)
    
    new_intentions = []
    context_lower = context_summary.lower()
    
    # Determine relevant categories based on context
    categories = ["creative", "technical", "social", "meta"]
    weights = [0.4, 0.3, 0.15, 0.15]  # Creative bias
    
    if "video" in context_lower or "ffmpeg" in context_lower:
        weights = [0.5, 0.25, 0.15, 0.1]
    if "git" in context_lower or "repository" in context_lower:
        weights = [0.3, 0.35, 0.25, 0.1]
    
    for _ in range(random.randint(2, 4)):
        category = random.choices(categories, weights=weights)[0]
        template = random.choice(INTENTION_TEMPLATES[category])
        
        # Check if this exact template is already active
        already_active = any(t["text"] == template for t in data["active"])
        if not already_active:
            data, intention = add_intention(data, template, category)
            new_intentions.append(intention)
    
    return data, new_intentions

def get_patterns(data):
    """Find intentions that have appeared 3+ times (patterns)."""
    patterns = [i for i in data["active"] if i["count"] >= 3]
    return sorted(patterns, key=lambda x: -x["count"])

def format_intentions(data, new_intentions=None):
    """Format intentions for display."""
    lines = []
    
    # Patterns first
    patterns = get_patterns(data)
    if patterns:
        lines.append("  📈 **Patterns (3+ appearances):**")
        for p in patterns:
            lines.append(f"    • {p['text']} (×{p['count']})")
        lines.append("")
    
    # Active intentions
    if data["active"]:
        lines.append("  🎯 **Active Intentions:**")
        for intention in data["active"]:
            if new_intentions and intention in new_intentions:
                lines.append(f"    ✨ {intention['text']} *(new)*")
            elif intention["count"] == 1:
                lines.append(f"    • {intention['text']}")
            else:
                lines.append(f"    • {intention['text']} (×{intention['count']})")
        lines.append("")
    
    # Stats
    lines.append(f"  📊 Stats: {data['stats']['total_created']} created, "
                 f"{data['stats']['total_completed']} completed, "
                 f"{data['stats']['sessions_count']} sessions")
    
    return "\n".join(lines)

# CLI for testing
if __name__ == "__main__":
    data = load_intentions()
    data["stats"]["sessions_count"] += 1
    
    print("=== Agnes Intentions Tracker ===")
    print(f"Active: {len(data['active'])}")
    print(f"Completed: {len(data['completed'])}")
    print(f"Stats: {data['stats']}")
    print()
    print("Patterns:", get_patterns(data))
    print()
    print(format_intentions(data))