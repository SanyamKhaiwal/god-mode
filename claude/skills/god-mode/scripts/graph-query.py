#!/usr/bin/env python3
"""
graph-query.py - symbol / dependency lookup over .godmode/project-map.json (stdlib only).

Usage:
  python graph-query.py [--map PATH] <command> <arg>

Commands:
  where <Name>            symbol definitions (exact or dotted-suffix match), max 20
  importers <file>        files that import <file> (internal edges), max 40
  deps <file>             files that <file> imports, max 40
  refs <Name>             files whose imported names include <Name>, max 40
  outline <file>          symbols in <file> with line numbers

<file> may be a full repo-relative path or a unique path suffix.
Exit codes: 0 ok, 1 usage/not found/ambiguous, 2 map missing.
"""

import json
import os
import sys

DEFAULT_MAP = os.path.join('.godmode', 'project-map.json')
BUILD_HINT = "python ~/.claude/skills/god-mode/scripts/build-graph.py ."
MAX_LINES = 40


def out(lines, limit=MAX_LINES):
    if len(lines) > limit:
        extra = len(lines) - (limit - 1)
        lines = lines[:limit - 1] + [f"... (+{extra} more)"]
    print('\n'.join(lines))


def resolve_path(graph, arg):
    """Return (path, None) or (None, error_lines)."""
    arg = arg.replace('\\', '/')
    if arg.startswith('./'):
        arg = arg[2:]
    nodes = graph.get('nodes', {})
    if arg in nodes:
        return arg, None
    cands = sorted(p for p in nodes if p.endswith('/' + arg) or p == arg)
    if len(cands) == 1:
        return cands[0], None
    if not cands:
        return None, [f"No indexed file matches '{arg}'."]
    return None, [f"Ambiguous path '{arg}', candidates:"] + [f"  {c}" for c in cands[:20]]


def cmd_where(graph, name):
    exact, suffix = [], []
    for path, node in graph.get('nodes', {}).items():
        for s in node.get('symbols', []):
            n = s['name']
            if n == name:
                exact.append((path, s))
            elif n.endswith('.' + name) or n.endswith('::' + name):
                suffix.append((path, s))
    hits = sorted(exact, key=lambda x: (x[0], x[1]['line'])) + sorted(suffix, key=lambda x: (x[0], x[1]['line']))
    if not hits:
        print(f"No symbol '{name}' found.")
        return 1
    lines = [f"{p}:{s['line']}  {s['kind']}  {s['name']}" for p, s in hits[:20]]
    if len(hits) > 20:
        lines.append(f"... (+{len(hits) - 20} more)")
    out(lines)
    return 0


def cmd_edges(graph, arg, direction):
    path, err = resolve_path(graph, arg)
    if err:
        out(err)
        return 1
    if direction == 'importers':
        res = sorted({e['from'] for e in graph.get('edges', []) if e['to'] == path})
        head = f"{len(res)} file(s) import {path}:"
    else:
        res = sorted({e['to'] for e in graph.get('edges', []) if e['from'] == path})
        head = f"{path} imports {len(res)} file(s):"
    lines = [head] + [f"  {r}" for r in res[:40]]
    if len(res) > 40:
        lines.append(f"  ... (+{len(res) - 40} more)")
    out(lines, 45)
    return 0


def cmd_refs(graph, name):
    res = sorted(p for p, n in graph.get('nodes', {}).items() if name in n.get('imported_names', []))
    if not res:
        print(f"No file imports the name '{name}'.")
        return 1
    lines = [f"{len(res)} file(s) import '{name}':"] + [f"  {r}" for r in res[:40]]
    if len(res) > 40:
        lines.append(f"  ... (+{len(res) - 40} more)")
    out(lines, 45)
    return 0


def cmd_outline(graph, arg):
    path, err = resolve_path(graph, arg)
    if err:
        out(err)
        return 1
    syms = sorted(graph['nodes'][path].get('symbols', []), key=lambda s: s['line'])
    if not syms:
        print(f"{path}: no symbols indexed.")
        return 0
    lines = [f"{path} ({len(syms)} symbols)"] + [f"  {s['line']:>5}  {s['kind']:<9} {s['name']}" for s in syms]
    out(lines)
    return 0


def main():
    args = sys.argv[1:]
    map_path = DEFAULT_MAP
    if '--map' in args:
        i = args.index('--map')
        if i + 1 >= len(args):
            print("--map needs a path", file=sys.stderr)
            return 1
        map_path = args[i + 1]
        del args[i:i + 2]
    if len(args) != 2 or args[0] not in ('where', 'importers', 'deps', 'refs', 'outline'):
        print("Usage: graph-query.py [--map PATH] where|importers|deps|refs|outline <arg>", file=sys.stderr)
        return 1
    if '--map' not in sys.argv:
        # Lazy build: create or incrementally refresh the default map on first use (≈1–2 s on 500+ files,
        # ≈0.3 s when nothing changed), so tasks that never ask a structural question pay nothing.
        build = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'build-graph.py')
        import subprocess
        subprocess.run([sys.executable, build, '.', map_path, '--quiet'], capture_output=True)
    if not os.path.exists(map_path):
        print(f"No project map at {map_path}. Build it with: {BUILD_HINT}", file=sys.stderr)
        return 2
    try:
        with open(map_path, 'r', encoding='utf-8') as f:
            graph = json.load(f)
    except Exception as e:
        print(f"Cannot read {map_path} ({e}). Rebuild with: {BUILD_HINT}", file=sys.stderr)
        return 2
    cmd, arg = args
    if cmd == 'where':
        return cmd_where(graph, arg)
    if cmd in ('importers', 'deps'):
        return cmd_edges(graph, arg, cmd)
    if cmd == 'refs':
        return cmd_refs(graph, arg)
    return cmd_outline(graph, arg)


if __name__ == '__main__':
    sys.exit(main())
