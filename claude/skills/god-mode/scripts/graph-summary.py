#!/usr/bin/env python3
"""
graph-summary.py — Generates a compact, human-readable summary of .godmode/project-map.json
for injection into God Mode researcher subagent briefs.
Outputs ~50-90 lines containing Hub nodes, architecture boundaries, dependencies, and key classes.

Usage:
  python graph-summary.py [project-map.json]
"""

import json
import sys
import os

def summarize(graph, brief=False, max_lines=None):
    """Return markdown lines for a loaded project-map dict.
    brief=True gives the compact variant (no class index, tighter caps)."""
    meta = graph.get('meta', {})
    nodes = graph.get('nodes', {})
    edges = graph.get('edges', [])
    communities = graph.get('communities', {})
    hubs = graph.get('hub_nodes', [])

    lines = []
    lines.append("# Project Architecture Map")
    lines.append(f"Files: {meta.get('total_files', len(nodes))} | Internal edges: {meta.get('total_edges', len(edges))}")
    coverage = meta.get('coverage', {})
    if coverage:
        parts = [f"{lang} {c.get('files', 0)} ({c.get('parser', '?')})" for lang, c in sorted(coverage.items())]
        lines.append("Coverage: " + ", ".join(parts))
    ext = meta.get('external_modules', {})
    if ext and not brief:
        top = list(ext.items())[:10]
        lines.append("External deps: " + ", ".join(f"{k} ({v})" for k, v in top))
    if brief:
        lines.append("Query: python ~/.claude/skills/god-mode/scripts/graph-query.py where <Name> | importers <file> | refs <Name> | outline <file>")
    lines.append("")

    if hubs:
        lines.append("## Hub Nodes (highest internal fan-in / blast radius)")
        for node_id, count in hubs[:10]:
            lines.append(f"  {node_id} - {count} incoming")
        lines.append("")

    if communities:
        lines.append("## Architecture Boundaries")
        items = sorted(communities.items())
        cap = 12 if brief else len(items)
        for domain, files in items[:cap]:
            n = 3 if brief else 6
            file_sample = ', '.join(files[:n])
            if len(files) > n:
                file_sample += f', ... (+{len(files)-n} more)'
            lines.append(f"  [{domain}] ({len(files)} files): {file_sample}")
        if len(items) > cap:
            lines.append(f"  ... (+{len(items)-cap} more domains)")
        lines.append("")

    dep_map = {}
    for e in edges:
        if e.get('relation') in ['imports', 'includes']:
            src = e.get('from', '')
            dst = e.get('to', '')
            if src and dst and src != dst:
                dep_map.setdefault(src, set()).add(dst)

    if dep_map:
        lines.append("## Key Dependency Connections")
        cap = 15 if brief else 25
        ranked = sorted(dep_map.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:cap]
        for src, dsts in ranked:
            lines.append(f"  {src} -> {', '.join(sorted(dsts)[:6])}")
        lines.append("")

    if not brief:
        lines.append("## Key Classes & Methods")
        class_count = 0
        for file_path, data in sorted(nodes.items()):
            classes = data.get('classes', [])
            methods = data.get('methods', [])
            if classes:
                class_names = [c.get('name') if isinstance(c, dict) else str(c) for c in classes]
                lines.append(f"  {file_path} -> classes: {', '.join(class_names)}")
                if methods:
                    method_names = [m.get('name') if isinstance(m, dict) else str(m) for m in methods[:5]]
                    lines.append(f"    methods: {', '.join(method_names)}")
                class_count += 1
                if class_count >= 20:
                    lines.append("  ... (additional classes omitted for brevity)")
                    break

    while lines and lines[-1] == "":
        lines.pop()
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines - 1] + ["... (truncated)"]
    return lines

def main():
    graph_path = sys.argv[1] if len(sys.argv) > 1 else '.godmode/project-map.json'
    if not os.path.exists(graph_path):
        print("No project-map.json found. Run build-graph.py first.", file=sys.stderr)
        sys.exit(0)

    try:
        with open(graph_path, 'r', encoding='utf-8') as f:
            graph = json.load(f)
    except Exception as e:
        print(f"Error reading graph: {e}", file=sys.stderr)
        sys.exit(1)

    print('\n'.join(summarize(graph)))

if __name__ == '__main__':
    main()
