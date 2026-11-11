#!/usr/bin/env python3
"""
build-graph.py — Zero-dependency Multi-Language AST Graph Builder for God Mode.
Parses Python, Java, and C++ source files to build a persistent dependency graph
in .godmode/project-map.json.

Features:
- Pure standard library (ast, re, os, sys, json, hashlib) — 0 external packages.
- Multi-language: Python (.py), Java (.java), C/C++ (.h, .hpp, .cpp, .cc, .cxx).
- Atomic kernel replace (os.replace) to prevent race conditions during concurrent agent access.
- Incremental SHA-256 caching: only re-parses modified files for sub-second updates (~20ms).
- Computes in-degree centrality (Hub Nodes) to pinpoint high-blast-radius files.

Usage:
  python build-graph.py [project_root] [output_path] [--quiet]
"""

import ast
import os
import sys
import re
import json
import hashlib
from collections import defaultdict
from typing import Dict, List, Set, Any, Optional

SUPPORTED_EXTENSIONS = {
    '.py': 'python',
    '.java': 'java',
    '.h': 'cpp',
    '.hpp': 'cpp',
    '.cpp': 'cpp',
    '.cc': 'cpp',
    '.cxx': 'cpp',
}

EXCLUDE_DIRS = {
    '.git', '.godmode', '__pycache__', 'node_modules', 'build', 'dist',
    '.idea', '.vscode', 'target', 'bin', 'obj', '.gradle'
}

def compute_file_hash(filepath: str) -> str:
    try:
        with open(filepath, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]
    except Exception:
        return ''

def normalize_rel_path(filepath: str, root: str) -> str:
    return os.path.relpath(filepath, root).replace('\\', '/')

class ProjectGraphBuilder:
    def __init__(self, root: str, output_path: str, quiet: bool = False):
        self.root = os.path.abspath(root)
        self.output_path = os.path.abspath(output_path)
        self.quiet = quiet
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: List[Dict[str, Any]] = []
        self.hub_scores: Dict[str, int] = {}
        self.existing_graph: Dict[str, Any] = {}

    def log(self, msg: str):
        if not self.quiet:
            print(msg, file=sys.stderr)

    def load_cache(self):
        if os.path.exists(self.output_path):
            try:
                with open(self.output_path, 'r', encoding='utf-8') as f:
                    self.existing_graph = json.load(f)
            except Exception:
                self.existing_graph = {}

    def find_source_files(self) -> List[str]:
        source_files = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [d for d in dirnames if not d.startswith('.') and d not in EXCLUDE_DIRS]
            for f in filenames:
                ext = os.path.splitext(f)[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    source_files.append(os.path.join(dirpath, f))
        return sorted(source_files)

    def parse_python(self, filepath: str, rel_path: str) -> Optional[Dict[str, Any]]:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        try:
            tree = ast.parse(source, filename=filepath)
        except SyntaxError:
            return None

        mod = rel_path.removesuffix('.py').replace('/', '.')
        classes = []
        functions = []
        imports = []
        file_edges = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                cls_id = f"{mod}.{node.name}"
                methods = []
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        args = [a.arg for a in item.args.args if a.arg != 'self']
                        ret = ast.unparse(item.returns) if item.returns else None
                        methods.append({'name': item.name, 'args': args, 'returns': ret, 'line': item.lineno})
                
                classes.append({'name': node.name, 'line': node.lineno, 'methods': methods})
                for b in node.bases:
                    base_name = getattr(b, 'id', None) or (ast.unparse(b) if hasattr(ast, 'unparse') else None)
                    if base_name:
                        file_edges.append({'from': cls_id, 'to': base_name, 'relation': 'inherits'})

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append({'name': node.name, 'line': node.lineno})

            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
                    file_edges.append({'from': mod, 'to': alias.name, 'relation': 'imports'})

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
                    file_edges.append({'from': mod, 'to': node.module, 'relation': 'imports'})

        return {
            'type': 'python',
            'path': rel_path,
            'module': mod,
            'classes': classes,
            'functions': functions,
            'imports': imports,
            'edges': file_edges,
        }

    def parse_java(self, filepath: str, rel_path: str) -> Optional[Dict[str, Any]]:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            code = f.read()

        clean = re.sub(r'//.*', '', code)
        clean = re.sub(r'/\*.*?\*/', '', clean, flags=re.DOTALL)

        pkg_match = re.search(r'package\s+([\w\.]+);', clean)
        pkg = pkg_match.group(1) if pkg_match else 'default'

        imports = re.findall(r'import\s+([\w\.\*]+);', clean)
        file_edges = [{'from': rel_path, 'to': imp, 'relation': 'imports'} for imp in imports]

        classes = []
        cls_pattern = r'(?:public\s+|protected\s+|private\s+)?(?:abstract\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w\s,]+))?'
        for m in re.finditer(cls_pattern, clean):
            cls_name, base_cls, ifaces = m.groups()
            full_cls = f"{pkg}.{cls_name}"
            classes.append({'name': cls_name, 'full': full_cls})
            if base_cls:
                file_edges.append({'from': full_cls, 'to': base_cls, 'relation': 'inherits'})
            if ifaces:
                for iface in ifaces.split(','):
                    file_edges.append({'from': full_cls, 'to': iface.strip(), 'relation': 'implements'})

        methods = []
        method_pattern = r'(?:public|protected|private)\s+(?:static\s+)?(?:final\s+)?([\w<>\[\]]+)\s+(\w+)\s*\(([^)]*)\)'
        for m in re.finditer(method_pattern, clean):
            ret_type, meth_name, args = m.groups()
            if meth_name not in ['if', 'for', 'while', 'switch']:
                methods.append({'name': meth_name, 'args': args.strip(), 'returns': ret_type})

        return {
            'type': 'java',
            'path': rel_path,
            'package': pkg,
            'classes': classes,
            'methods': methods,
            'imports': imports,
            'edges': file_edges,
        }

    def parse_cpp(self, filepath: str, rel_path: str) -> Optional[Dict[str, Any]]:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            code = f.read()

        clean = re.sub(r'//.*', '', code)
        clean = re.sub(r'/\*.*?\*/', '', clean, flags=re.DOTALL)

        includes = re.findall(r'#include\s+["<]([\w\./\\]+)[">]', clean)
        file_edges = [{'from': rel_path, 'to': inc, 'relation': 'includes'} for inc in includes]

        classes = []
        cls_pattern = r'class\s+(\w+)(?:\s*:\s*(?:public|protected|private)\s+(\w+))?'
        for m in re.finditer(cls_pattern, clean):
            cls_name, base_cls = m.groups()
            classes.append({'name': cls_name})
            if base_cls:
                file_edges.append({'from': f"{rel_path}:{cls_name}", 'to': base_cls, 'relation': 'inherits'})

        methods = []
        method_pattern = r'(?:virtual\s+)?([\w:<>]+)\s+(?:(\w+)::)?(\w+)\s*\(([^)]*)\)'
        for m in re.finditer(method_pattern, clean):
            ret_type, cls_scope, meth_name, args = m.groups()
            if meth_name not in ['if', 'for', 'while', 'switch', 'return']:
                scope = f"{cls_scope}::" if cls_scope else ""
                methods.append({'name': f"{scope}{meth_name}", 'args': args.strip(), 'returns': ret_type})

        return {
            'type': 'cpp',
            'path': rel_path,
            'classes': classes,
            'methods': methods[:15],
            'includes': includes,
            'edges': file_edges,
        }

    def build(self):
        self.load_cache()
        cached_nodes = self.existing_graph.get('nodes', {})
        files = self.find_source_files()
        
        reparsed_count = 0
        all_edges = []

        for filepath in files:
            rel_path = normalize_rel_path(filepath, self.root)
            current_hash = compute_file_hash(filepath)
            
            # Check incremental cache
            if rel_path in cached_nodes and cached_nodes[rel_path].get('hash') == current_hash:
                node_data = cached_nodes[rel_path]
                self.nodes[rel_path] = node_data
                all_edges.extend(node_data.get('edges', []))
                continue

            # File is new or changed: reparse
            ext = os.path.splitext(filepath)[1].lower()
            res = None
            if ext == '.py':
                res = self.parse_python(filepath, rel_path)
            elif ext == '.java':
                res = self.parse_java(filepath, rel_path)
            elif ext in ['.h', '.hpp', '.cpp', '.cc', '.cxx']:
                res = self.parse_cpp(filepath, rel_path)

            if res:
                res['hash'] = current_hash
                self.nodes[rel_path] = res
                all_edges.extend(res.get('edges', []))
                reparsed_count += 1

        # Deduplicate edges
        seen = set()
        unique_edges = []
        in_degree = defaultdict(int)

        for e in all_edges:
            key = (e['from'], e['to'], e['relation'])
            if key not in seen:
                seen.add(key)
                unique_edges.append(e)
                in_degree[e['to']] += 1

        self.edges = unique_edges
        self.hub_scores = dict(sorted(in_degree.items(), key=lambda x: -x[1]))

        # Group into top-level architecture domains
        communities = defaultdict(list)
        for rel_path in self.nodes.keys():
            top = rel_path.split('/')[0] if '/' in rel_path else 'root'
            communities[top].append(rel_path)

        graph_data = {
            'meta': {
                'total_files': len(self.nodes),
                'total_edges': len(self.edges),
                'reparsed_files': reparsed_count,
            },
            'hub_nodes': list(self.hub_scores.items())[:12],
            'communities': dict(communities),
            'nodes': self.nodes,
            'edges': self.edges,
        }

        # Atomic file write via PID-based temporary file
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        temp_path = f"{self.output_path}.tmp.{os.getpid()}"
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(graph_data, f, indent=2)
        os.replace(temp_path, self.output_path)

        self.log(f"God Mode Graph: {len(self.nodes)} files indexed ({reparsed_count} re-parsed), {len(self.edges)} edges.")

def main():
    root = '.'
    output = '.godmode/project-map.json'
    quiet = False

    args = sys.argv[1:]
    if '--quiet' in args:
        quiet = True
        args.remove('--quiet')

    if len(args) > 0:
        root = args[0]
    if len(args) > 1:
        output = args[1]
    else:
        output = os.path.join(root, '.godmode', 'project-map.json')

    builder = ProjectGraphBuilder(root, output, quiet=quiet)
    builder.build()

if __name__ == '__main__':
    main()

