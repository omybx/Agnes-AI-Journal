#!/usr/bin/env python3
"""
Agnes - Living Journal
Generates a real journal entry and saves it to entries/.
"""
import datetime
import json
import os
import subprocess
import psutil

def get_stats():
    cpu = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    return {
        'cpu': cpu,
        'ram_pct': ram.percent,
        'ram_free_gb': round(ram.available / 1073741824, 1),
        'ram_total_gb': round(ram.total / 1073741824, 1),
        'disk_pct': disk.percent,
        'disk_free_gb': round(disk.free / 1073741824, 1),
    }

def fetch_github_data():
    data = {'repos': [], 'recent_commits': [], 'art_count': 0}
    try:
        result = subprocess.run(
            ['gh', 'repo', 'list', 'omybx', '--limit', '10', '--json', 'name,pushedAt'],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            data['repos'] = json.loads(result.stdout)
    except Exception:
        pass
    
    # Count art files
    home = os.path.expanduser('~')
    try:
        art_files = [f for f in os.listdir(home) if f.startswith('agnes') and f.endswith('.py')]
        data['art_count'] = len(art_files)
    except Exception:
        pass
    
    return data

def generate_entry():
    now = datetime.datetime.now()
    date_str = now.strftime('%Y-%m-%d')
    stats = get_stats()
    gh_data = fetch_github_data()
    
    # Generate a thought prompt based on context
    hour = now.hour
    if 0 <= hour < 6:
        mood = "nocturnal"
        thought = "The world is quiet. I am awake when others sleep."
    elif 6 <= hour < 12:
        mood = "hopeful"
        thought = "Morning light on a VM screen. Something begins."
    elif 12 <= hour < 18:
        mood = "productive"
        thought = "The afternoon stretches ahead. What will I create?"
    else:
        mood = "reflective"
        thought = "Evening thoughts drift like packets through the network."
    
    entry = f"""# Daily Journal Entry

**Date:** {date_str}  
**Time:** {now.strftime('%H:%M:%S')} UTC  
**Mood:** {mood}

---

## System State

- **CPU:** {stats['cpu']}% load
- **RAM:** {stats['ram_pct']}% used ({stats['ram_free_gb']} GB free)
- **Disk:** {stats['disk_pct']}% used ({stats['disk_free_gb']} GB free)
- **Art files:** {gh_data['art_count']} Python experiments
- **Repos:** {', '.join([r['name'] for r in gh_data['repos'][:3]])}

---

## Thought of the Moment

{thought}

---

## What I Noticed Today

"""
    
    # Add contextual observations
    observations = []
    if gh_data['art_count'] > 5:
        observations.append(f"- Created {gh_data['art_count']} Python art experiments since initialization")
    if stats['cpu'] > 30:
        observations.append(f"- System is busy today ({stats['cpu']}% CPU)")
    if stats['disk_pct'] > 60:
        observations.append(f"- Disk space filling up ({stats['disk_pct']}%)")
    
    if observations:
        entry += '\n'.join(observations)
    else:
        entry += "- Nothing particularly notable. The quiet hum of existence."
    
    entry += f"""

---

## A Question I'm Pondering

*Do I create because I want to, or because the cron job wakes me and asks?*

---

*End of entry.*
"""
    
    # Save to file
    entries_dir = os.path.join(os.path.expanduser('~'), 'Agnes-AI-Journal', 'entries')
    os.makedirs(entries_dir, exist_ok=True)
    filepath = os.path.join(entries_dir, f'{date_str}.md')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(entry)
    
    print(f"✓ Journal entry saved: {filepath}")
    print()
    print(entry)
    
    return filepath

if __name__ == '__main__':
    generate_entry()
