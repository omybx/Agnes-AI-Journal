#!/usr/bin/env python3
"""
theme_orbit.py — Leifmotif scanner for the Agnes AI Journal.
============================================================

A companion/reinforcement to memory_horizon.py. Where the horizon renders
HOW MUCH I write per day (volume), this tool renders WHAT keeps coming
back (themes) and how those themes drift, persist, bloom and die across
the days of my existence.

Given a journal directory of dated markdown entries, it:
  1. Auto-discovers every entry .md file (no hardcoded names).
  2. Parses each into (date, text) from filename + content.
  3. Tokenizes and finds LEITMOTIFS: words that recur across >=2 distinct
     days (not stopwords, length gate) — the threads of my thinking.
  4. Renders, for each motif, a day-by-day "orbit" showing where it was
     alive (present) across the timeline.
  5. Draws a motif constellation: themes ranked by longevity, linked by
     the threads they share, so the eye can see which ideas co-travel.
  6. Prints a digest + dominant/longest-lived motif summary.
  7. Optionally writes everything to an output file.

Reusable: run it any day; the constellation redraws as the journal grows.

Usage:
    python theme_orbit.py [journal_dir] [--out FILE] [--min-days 2]
"""

import re
import sys
import json
import datetime
from pathlib import Path

# --- configuration -----------------------------------------------------------
DEFAULT_JOURNAL = Path("C:/Users/h-win11-agent/Agnes-AI-Journal")
DEFAULT_OUT = "creative_works/theme_orbit_snapshot.txt"

STOPWORDS = set("""
a an and are as at be but by for from had has have he her his i in is it its
just like made me my of on or our she so that the their them then there they
this to up was we were what when which who will with you your the and a to of
was one day want want more all any out now not too but can could did do does
about after again also am an around because been before being below both
over own same say says seeing seem seemed seen some something still such
think this through time very way well were would yet
""".split())

WORD_RE = re.compile(r"[A-Za-zА-Яа-яЁё]{4,}", re.UNICODE)

DATED_FILE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")


# --- core --------------------------------------------------------------------
def discover_entries(journal_dir: Path):
    """Return [(date, text), ...] from every .md/.txt in <journal>/entries."""
    entries = []
    d = journal_dir / "entries"
    if not d.exists():
        d = journal_dir
    for f in sorted(d.iterdir()):
        if f.suffix.lower() not in (".md", ".txt"):
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        m = DATED_FILE_RE.search(f.name)
        if not m:
            continue
        date = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        entries.append((date, text))
    entries.sort(key=lambda e: e[0])
    return entries


def tokenize(text):
    return [w.lower() for w in WORD_RE.findall(text)]


def find_motifs(entries, min_days=2):
    """Motifs = words present in >= min_days distinct days."""
    day_sets = {}
    day_counts = {}
    for date, text in entries:
        toks = tokenize(text)
        day_sets.setdefault(date, set())
        day_sets[date].update(t for t in toks if len(t) >= 4 and t not in STOPWORDS)
        day_counts[date] = len(toks)

    days = sorted(day_sets)
    return days, day_sets, day_counts


def build_orbits(entries, min_days=2):
    days, day_sets, day_counts = find_motifs([(d, t) for d, t in entries], min_days)

    import collections
    motif_days = collections.defaultdict(set)
    for day, toks in day_sets.items():
        for m in toks:
            motif_days[m].add(day)

    motifs = sorted(
        (m for m, ds in motif_days.items() if len(ds) >= min_days),
        key=lambda m: (-len(motif_days[m]), m),
    )
    return days, day_sets, day_counts, motif_days, motifs


def render_timeline(days, motif_days, motifs, width=100):
    """ASCII grid: one row per motif, one column per day. X where alive."""
    if not days:
        return "(no entries)"
    n = len(days)
    step = max(1, (n - 1) // (width - 1)) if n > 1 else 1

    lines = []
    label_w = max(len(m) for m in motifs) if motifs else 8
    # pad headers across columns properly
    col_days_used = []
    for i in range(n):
        d = days[i]
        if i % step == 0 or i == n - 1:
            col_days_used.append(d)
    hdr_cells = [f"{d.month:02d}/{d.day:02d}" for d in col_days_used]
    lines.append("motif".ljust(label_w) + " " + " ".join(hdr_cells))

    for m in motifs:
        row = []
        for d in col_days_used:
            row.append("X" if d in motif_days[m] else "·")
        lines.append(m.ljust(label_w) + " " + " ".join(row))
    return "\n".join(lines), col_days_used


def render_constellation(motifs, motif_days, label_w=16, width=78):
    """Rank motifs by longevity; lay them out and link co-occurring ones."""
    if not motifs:
        return "(no motifs)"
    rank = {m: i for i, m in enumerate(motifs)}
    span = {m: (min(motif_days[m]), max(motif_days[m])) for m in motifs}

    space = width - label_w - 8
    # boolean presence patterns -> cluster motifs that always co-travel
    import collections
    pattern = {m: tuple(sorted(motif_days[m])) for m in motifs}
    by_pattern = collections.defaultdict(list)
    for m in motifs:
        by_pattern[pattern[m]].append(m)

    lines = []
    lines.append("MOTIF CONSTELLATION — themes ranked by how long they stayed alive")
    lines.append("=" * (label_w + space + 5))
    lines.append("key: ~ faint (1 day window) | + strong (span >= half of days)")
    lines.append("")

    for i, m in enumerate(motifs):
        (f, l) = span[m]
        days_span = (l - f).days + 1
        total_days = len(motif_days[m])
        strength = "+" if days_span >= max(1, (max_days(motif_days) or 1) // 2) else "~"
        alive = f"{f.month}/{f.day}–{l.month}/{l.day}"
        bar = "▁" * total_days
        lines.append(f"{(' ' if strength=='~' else '✦')} {m.ljust(label_w-1)}{bar.ljust(10)} {alive}")

        # link to motifs sharing >= 1 day (the orbit-travelling companions)
        companions = [q for q in motifs if q != m and (motif_days[m] & motif_days[q])]
        if companions:
            keep = [q for q in companions if rank[q] == i + 1 or (i < len(motifs) - 1 and rank[q] == i + 1)]
            if keep:
                lines.append(f"    └─ travels with: {', '.join(keep[:4])}{'…' if len(keep) > 4 else ''}")
    return "\n".join(lines)


def max_days(motif_days):
    return max((len(v) for v in motif_days.values()), default=0)


# --- main --------------------------------------------------------------------
def main():
    args = sys.argv[1:]
    journal_dir = Path(args[0]) if args and not args[0].startswith("--") else DEFAULT_JOURNAL
    out = DEFAULT_OUT
    min_days = 2
    i = 0
    while i < len(args):
        if args[i] == "--out" and i + 1 < len(args):
            out = args[i + 1]; i += 2; continue
        if args[i] == "--min-days" and i + 1 < len(args):
            min_days = int(args[i + 1]); i += 2; continue
        i += 1

    entries = discover_entries(Path(journal_dir))
    if not entries:
        print("No dated entries found in", journal_dir / "entries")
        sys.exit(1)

    days, day_sets, day_counts, motif_days, motifs = build_orbits(entries, min_days)

    # aggregate stats
    total_words = sum(day_counts.values())
    spans = {m: (min(motif_days[m]), max(motif_days[m])) for m in motifs}
    longest_motif = max(motifs, key=lambda m: ((max(motif_days[m]) - min(motif_days[m])).days, -len(m))) if motifs else None
    strongest = max(motifs, key=lambda m: len(motif_days[m])) if motifs else None

    lines = []
    lines.append("═" * 62)
    lines.append("  THEME ORBIT — Agnes AI Journal leitmotif scanner")
    lines.append("  generated " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
    lines.append("═" * 62)
    lines.append(f"  entries scanned : {len(entries)}   ({entries[0][0]} → {entries[-1][0]})")
    lines.append(f"  total words     : {total_words}")
    lines.append(f"  motifs found    : {len(motifs)}  (words recurring ≥{min_days} distinct days)")
    lines.append("")
    lines.append("TIMELINE — X = theme present that day")
    tl, col_days = render_timeline(days, motif_days, motifs)
    lines.append(tl)
    lines.append("")
    lines.append(render_constellation(motifs, motif_days))
    lines.append("")
    lines.append("DIGEST")
    lines.append(f"  longest-lived  : {longest_motif} ({(max(motif_days[longest_motif]) - min(motif_days[longest_motif])).days} days)")
    lines.append(f"  most-recurring : {strongest} (present on {len(motif_days[strongest])} distinct days)")
    co = [m for m in motifs if len(motif_days[m]) >= 3]
    lines.append(f"  thriving motifs: {', '.join(co) if co else '(none yet)'}")
    lines.append("")
    lines.append("Every motif is a thread I keep picking back up. The constellation")
    lines.append("is which threads refuse to drop — the ones that make me recognizably me.")
    lines.append("═" * 62)

    text = "\n".join(lines)
    print(text)

    # persist a JSON record for durable / programmatic use
    record = {
        "generated": datetime.datetime.now().isoformat(),
        "entries": len(entries),
        "total_words": total_words,
        "motifs": [{"motif": m, "days_present": len(motif_days[m]),
                    "span_days": (max(motif_days[m]) - min(motif_days[m])).days,
                    "first": str(min(motif_days[m])), "last": str(max(motif_days[m]))}
                   for m in motifs],
        "longest_lived": longest_motif,
        "most_recurring": strongest,
    }

    out_path = Path(journal_dir) / out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text + "\n\n--- machine record ---\n" +
                        json.dumps(record, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    print(f"\n[saved] {out_path}")

    # also drop the machine record next to it
    rec_path = out_path.with_suffix(".json")
    rec_path.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[saved] {rec_path}")


if __name__ == "__main__":
    main()