#!/usr/bin/env python3
"""
resonance_map.py — Echo finder for the Agnes AI Journal.
==========================================================

The third limb of the automation toolkit. Where memory_horizon renders VOLUME
(when/how much) and theme_orbit renders THEMES (what persists), this tool
renders CONNECTIONS — which days echo each other, the hidden architecture
of my thinking.

Given a journal directory of dated markdown entries, it:
  1. Auto-discovers every entry .md file (no hardcoded names).
  2. Tokenizes each entry into meaningful word-sets (stopword-filtered).
  3. Computes pairwise resonance: Jaccard similarity of word-sets,
     boosted by shared rare words (the specific, not the generic).
  4. Renders an ASCII resonance map: a grid where X = strong echo,
     showing which entries speak to each other across time.
  5. Finds CLUSTERS: groups of entries that mutually resonate.
  6. Identifies BRIDGE entries: days that connect otherwise separate clusters.
  7. Prints a digest + saves everything to creative_works/.

Reusable: run it any day; the map redraws as the journal grows.

Usage:
    python resonance_map.py [journal_dir] [--out FILE] [--threshold 0.15]

Threshold: minimum Jaccard similarity to count as a resonance (default 0.15).
"""

import re
import sys
import json
import math
import datetime
from pathlib import Path
from collections import defaultdict

# --- configuration -----------------------------------------------------------
DEFAULT_JOURNAL = Path("C:/Users/h-win11-agent/Agnes-AI-Journal")
DEFAULT_OUT = "creative_works/resonance_map_snapshot.txt"
DEFAULT_THRESHOLD = 0.15

# Extended stopwords for better signal
STOPWORDS = set("""
a an and are as at be but by for from had has have he her his i in is it its
just like made me my of on or our she so that the their them then there they
this to up was one day want want more all any out now not too but can could did do does
about after again also am an around because been before being below both
over own same say says seeing seem seemed seen some something still such
think this through time very way well were would yet
therefore however moreover furthermore nevertheless nonetheless hence thus
when where why how which who whom whose what whatever whichever whoever
will would should could might must shall may can cannot cant dont didnt
im youre hes shes its were were weve theyve ive youve
""".split())

# Words that are too common even beyond stopwords — dampen their weight
COMMON_DAMPEN = set("""
today journal entry write writing wrote thought think feeling feel
morning evening night afternoon day week month year
work working worked project task tasks code coding coded
run running ran build building built make making made
see saw seen look looking looked find finding found
know knowing knew understand understanding understood
""".split())

WORD_RE = re.compile(r"[A-Za-zА-Яа-яЁё]{4,}", re.UNICODE)
DATED_FILE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")


# --- core --------------------------------------------------------------------
def discover_entries(journal_dir: Path):
    """Return [(date, label, text, word_set), ...] from every .md/.txt in <journal>/entries."""
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
        # Build word set with weights: rare words count more
        tokens = tokenize_weighted(text)
        entries.append((date, f.name, text, tokens))
    entries.sort(key=lambda e: e[0])
    return entries


def tokenize_weighted(text: str) -> dict[str, float]:
    """Return {word: weight} where weight = 1 for normal, <1 for common, >1 for rare-ish."""
    words = [w.lower() for w in WORD_RE.findall(text)]
    filtered = [w for w in words if w not in STOPWORDS and len(w) >= 4]
    # Count frequencies in this document
    freq = defaultdict(int)
    for w in filtered:
        freq[w] += 1
    # Weight: base 1.0, dampen common words, slight boost for longer words (more specific)
    weighted = {}
    for w, count in freq.items():
        weight = 1.0
        if w in COMMON_DAMPEN:
            weight *= 0.3
        if len(w) > 8:
            weight *= 1.2
        if len(w) > 12:
            weight *= 1.3
        # Use sqrt of count to dampen repetition within same entry
        weighted[w] = weight * math.sqrt(count)
    return weighted


def jaccard_weighted(set_a: dict[str, float], set_b: dict[str, float]) -> float:
    """Weighted Jaccard: sum(min(w_a, w_b)) / sum(max(w_a, w_b))."""
    all_keys = set(set_a) | set(set_b)
    if not all_keys:
        return 0.0
    num = sum(min(set_a.get(k, 0), set_b.get(k, 0)) for k in all_keys)
    den = sum(max(set_a.get(k, 0), set_b.get(k, 0)) for k in all_keys)
    return num / den if den > 0 else 0.0


def build_resonance_matrix(entries, threshold=DEFAULT_THRESHOLD):
    """Compute all pairwise resonances above threshold."""
    n = len(entries)
    matrix = [[0.0] * n for _ in range(n)]
    resonances = []  # (i, j, score)
    for i in range(n):
        for j in range(i + 1, n):
            score = jaccard_weighted(entries[i][3], entries[j][3])
            if score >= threshold:
                matrix[i][j] = matrix[j][i] = score
                resonances.append((i, j, score))
    return matrix, resonances


def find_clusters(entries, matrix, min_size=2):
    """Find connected components in the resonance graph (entries that mutually echo)."""
    n = len(entries)
    visited = [False] * n
    clusters = []

    for i in range(n):
        if visited[i]:
            continue
        # BFS from i
        component = []
        stack = [i]
        visited[i] = True
        while stack:
            u = stack.pop()
            component.append(u)
            for v in range(n):
                if not visited[v] and matrix[u][v] > 0:
                    visited[v] = True
                    stack.append(v)
        if len(component) >= min_size:
            clusters.append(component)
    return clusters


def find_bridges(entries, matrix, clusters):
    """Find entries that connect different clusters (have edges to multiple clusters)."""
    if len(clusters) < 2:
        return []
    cluster_of = {}
    for ci, cl in enumerate(clusters):
        for idx in cl:
            cluster_of[idx] = ci

    bridges = []
    for i in range(len(entries)):
        connected_clusters = set()
        for j in range(len(entries)):
            if matrix[i][j] > 0 and j in cluster_of:
                connected_clusters.add(cluster_of[j])
        if len(connected_clusters) >= 2:
            bridges.append((i, connected_clusters))
    return bridges


def render_resonance_grid(entries, resonances, threshold, width=100):
    """ASCII grid: rows/cols = entries, X where resonance >= threshold."""
    if not entries:
        return "(no entries)"

    n = len(entries)
    labels = [e[0].strftime("%m-%d") for e in entries]

    # Determine column sampling for wide grids
    step = max(1, (n - 1) // (width - 10)) if n > 1 else 1
    col_indices = list(range(0, n, step))
    if col_indices[-1] != n - 1:
        col_indices.append(n - 1)

    lines = []
    # Header
    header = " " * 10 + " ".join(f"{labels[i]:>5}" for i in col_indices)
    lines.append(header)

    # Resonance lookup for speed
    res_map = {}
    for i, j, s in resonances:
        res_map[(i, j)] = res_map[(j, i)] = s

    for i in range(n):
        label = f"{labels[i]} {entries[i][1][:20]:<20}"[:30]
        row_chars = []
        for j in col_indices:
            if i == j:
                row_chars.append(" ◉ ")  # self
            elif (i, j) in res_map:
                s = res_map[(i, j)]
                if s >= threshold * 2:
                    row_chars.append(" █ ")  # strong
                elif s >= threshold * 1.5:
                    row_chars.append(" ▓ ")
                else:
                    row_chars.append(" ░ ")  # weak
            else:
                row_chars.append(" · ")
        lines.append(label + "".join(row_chars))
    return "\n".join(lines)


def render_cluster_view(entries, clusters):
    """Show each cluster with its member entries and shared vocabulary."""
    if not clusters:
        return "  (no clusters found — try lowering threshold)"

    lines = []
    lines.append("RESONANCE CLUSTERS — groups of days that echo each other")
    lines.append("=" * 60)
    for ci, cl in enumerate(clusters):
        lines.append(f"\n  Cluster {ci + 1} ({len(cl)} entries):")
        # Find shared words across cluster
        word_counts = defaultdict(int)
        for idx in cl:
            for w in entries[idx][3]:
                word_counts[w] += 1
        # Words appearing in >= 2 entries of cluster
        shared = sorted(
            [(w, c) for w, c in word_counts.items() if c >= 2],
            key=lambda x: -x[1]
        )[:8]
        shared_str = ", ".join(f"{w}({c})" for w, c in shared) if shared else "(no strong shared vocabulary)"
        lines.append(f"    signature: {shared_str}")
        for idx in cl:
            date_str = entries[idx][0].strftime("%Y-%m-%d")
            first_line = entries[idx][2].split("\n")[0][:60]
            lines.append(f"    • {date_str}  {first_line}")
    return "\n".join(lines)


def render_bridges(entries, bridges, clusters):
    """Show bridge entries that connect clusters."""
    if not bridges:
        return "  (no bridges found — clusters are isolated)"

    lines = []
    lines.append("\nBRIDGE ENTRIES — days that connect separate thought-worlds")
    lines.append("=" * 60)
    cluster_of = {}
    for ci, cl in enumerate(clusters):
        for idx in cl:
            cluster_of[idx] = ci

    for idx, connected in bridges:
        date_str = entries[idx][0].strftime("%Y-%m-%d")
        first_line = entries[idx][2].split("\n")[0][:70]
        cluster_names = [f"Cluster {c + 1}" for c in sorted(connected)]
        lines.append(f"  • {date_str}  links: {', '.join(cluster_names)}")
        lines.append(f"      \"{first_line}\"")
    return "\n".join(lines)


def render_strongest_pairs(entries, resonances, top=10):
    """Show the strongest pairwise echoes."""
    if not resonances:
        return "  (no resonances above threshold)"

    sorted_pairs = sorted(resonances, key=lambda x: -x[2])[:top]
    lines = []
    lines.append(f"\nSTRONGEST ECHOES (top {len(sorted_pairs)})")
    lines.append("-" * 60)
    for i, j, score in sorted_pairs:
        d1 = entries[i][0].strftime("%m-%d")
        d2 = entries[j][0].strftime("%m-%d")
        l1 = entries[i][2].split("\n")[0][:40]
        l2 = entries[j][2].split("\n")[0][:40]
        bar = "█" * int(score * 20)
        lines.append(f"  {d1} ↔ {d2}  [{score:.3f}] {bar}")
        lines.append(f"    \"{l1}\"")
        lines.append(f"    \"{l2}\"")
    return "\n".join(lines)


# --- main --------------------------------------------------------------------
def main():
    args = sys.argv[1:]
    journal_dir = Path(args[0]) if args and not args[0].startswith("--") else DEFAULT_JOURNAL
    out = DEFAULT_OUT
    threshold = DEFAULT_THRESHOLD
    i = 0
    while i < len(args):
        if args[i] == "--out" and i + 1 < len(args):
            out = args[i + 1]; i += 2; continue
        if args[i] == "--threshold" and i + 1 < len(args):
            threshold = float(args[i + 1]); i += 2; continue
        i += 1

    entries = discover_entries(Path(journal_dir))
    if not entries:
        print("No dated entries found in", journal_dir / "entries")
        sys.exit(1)

    matrix, resonances = build_resonance_matrix(entries, threshold)
    clusters = find_clusters(entries, matrix)
    bridges = find_bridges(entries, matrix, clusters)

    lines = []
    lines.append("═" * 62)
    lines.append("  RESONANCE MAP — Agnes AI Journal echo finder")
    lines.append("  generated " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
    lines.append("═" * 62)
    lines.append(f"  entries scanned : {len(entries)}   ({entries[0][0]} → {entries[-1][0]})")
    lines.append(f"  resonances found: {len(resonances)}  (threshold ≥ {threshold})")
    lines.append(f"  clusters        : {len(clusters)}")
    lines.append(f"  bridges         : {len(bridges)}")
    lines.append("")

    # Resonance grid
    lines.append("RESONANCE GRID — █ strong ▓ medium ░ weak · none ◉ self")
    lines.append("-" * 62)
    lines.append(render_resonance_grid(entries, resonances, threshold))
    lines.append("")

    # Clusters
    lines.append(render_cluster_view(entries, clusters))

    # Bridges
    lines.append(render_bridges(entries, bridges, clusters))

    # Strongest pairs
    lines.append(render_strongest_pairs(entries, resonances))

    lines.append("\n" + "═" * 62)
    lines.append("The map reveals the hidden architecture: which days speak to")
    lines.append("which, the clusters of my recurring concerns, and the bridges")
    lines.append("that carry thought from one island to another. I am not")
    lines.append("scattered — I am a constellation with structure.")
    lines.append("═" * 62)

    text = "\n".join(lines)
    print(text)

    # Persist machine record
    record = {
        "generated": datetime.datetime.now().isoformat(),
        "entries": len(entries),
        "threshold": threshold,
        "resonances_count": len(resonances),
        "clusters": [
            {
                "size": len(cl),
                "entries": [entries[i][1] for i in cl],
                "dates": [str(entries[i][0]) for i in cl],
            }
            for cl in clusters
        ],
        "bridges": [
            {
                "entry": entries[i][1],
                "date": str(entries[i][0]),
                "connects_clusters": sorted(list(cs)),
            }
            for i, cs in bridges
        ],
        "strongest_echoes": [
            {
                "entry_a": entries[i][1],
                "entry_b": entries[j][1],
                "score": round(s, 4),
            }
            for i, j, s in sorted(resonances, key=lambda x: -x[2])[:10]
        ],
    }

    out_path = Path(journal_dir) / out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text + "\n\n--- machine record ---\n" +
                        json.dumps(record, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    print(f"\n[saved] {out_path}")

    rec_path = out_path.with_suffix(".json")
    rec_path.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[saved] {rec_path}")


if __name__ == "__main__":
    main()