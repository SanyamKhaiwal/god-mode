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

    meta = graph.get('meta', {})
    nodes = graph.get('nodes', {})
    edges = graph.get('edges', [])
    communities = graph.get('communities', {})
    hubs = graph.get('hub_nodes', [])

    lines = []
    lines.append("# Project Architecture Map")
    lines.append(f"Files: {meta.get('total_files', len(nodes))} | Edges: {meta.get('total_edges', len(edges))}")
    lines.append("")

    # Top Hub Nodes
    if hubs:
        lines.append("## Hub Nodes (highest dependency fan-in / blast radius)")
        for node_id, count in hubs[:10]:
            lines.append(f"  {node_id} — {count} incoming references")
        lines.append("")

    # Architecture Boundaries
    if communities:
        lines.append("## Architecture Boundaries")
        for domain, files in sorted(communities.items()):
            file_sample = ', '.join(files[:6])
            if len(files) > 6:
                file_sample += f', ... (+{len(files)-6} more)'
            lines.append(f"  [{domain}] ({len(files)} files): {file_sample}")
        lines.append("")

    # Direct Dependencies Map
    dep_map = {}
    for e in edges:
        if e.get('relation') in ['imports', 'includes']:
            src = e.get('from', '')
            dst = e.get('to', '')
            if src and dst and src != dst:
                dep_map.setdefault(src, set()).add(dst)

    if dep_map:
        lines.append("## Key Dependency Connections")
        for src, dsts in sorted(dep_map.items())[:25]:
            lines.append(f"  {src} -> {', '.join(sorted(dsts)[:6])}")
        lines.append("")

    # Class & Method Index
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

    print('\n'.join(lines))

if __name__ == '__main__':
    main()

