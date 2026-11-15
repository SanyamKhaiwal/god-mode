#!/usr/bin/env python3
"""
build-graph.py — Zero-dependency Multi-Language Graph Builder for God Mode.
Parses Python (AST), Java, C/C++ and JS/TS (regex) source files to build a persistent
dependency graph in .godmode/project-map.json.

Features:
- Pure standard library (ast, re, os, sys, json, hashlib) — 0 external packages.
- Multi-language: Python (.py), Java (.java), C/C++ (.h, .hpp, .cpp, .cc, .cxx),
  JS/TS (.js .jsx .ts .tsx .mjs .cjs).
- Only internal edges (target resolves to a repo file) are stored in `edges`;
  external modules are counted in meta.external_modules (top 30).
- Atomic kernel replace (os.replace) to prevent race conditions during concurrent agent access.
- Incremental SHA-256 caching: only re-parses modified files.
- Computes in-degree centrality (Hub Nodes) over internal edges only.
- Also writes graph-brief.txt (<= 60 lines) next to the output, for researcher agents.

Usage:
  python build-graph.py [project_root] [output_path] [--quiet]
"""

import ast
import os
import sys
import re
import json
import hashlib
import importlib.util
from collections import defaultdict
from typing import Dict, List, Any, Optional

SUPPORTED_EXTENSIONS = {
    '.py': 'python',
    '.java': 'java',
    '.h': 'cpp',
    '.hpp': 'cpp',
    '.cpp': 'cpp',
    '.cc': 'cpp',
    '.cxx': 'cpp',
    '.js': 'javascript',
    '.jsx': 'javascript',
    '.mjs': 'javascript',
    '.cjs': 'javascript',
    '.ts': 'typescript',
    '.tsx': 'typescript',
}

JS_EXTS = ['.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs']
CACHE_VERSION = 4
BRIEF_MAX_LINES = 60

EXCLUDE_DIRS = {
    '.git', '.godmode', '__pycache__', 'node_modules', 'build', 'dist',
    '.idea', '.vscode', 'target', 'bin', 'obj', '.gradle',
    '.next', 'coverage', '.venv', 'venv'
}

JS_FROM_RE = re.compile(r"""\b(?:import|export)\s+(?:type\s+)?[^'";()]*?\bfrom\s*['"]([^'"\n]+)['"]""")
JS_BARE_RE = re.compile(r"""\bimport\s*['"]([^'"\n]+)['"]""")
JS_REQ_RE = re.compile(r"""\brequire\s*\(\s*['"]([^'"\n]+)['"]\s*\)""")
JS_DYN_RE = re.compile(r"""\bimport\s*\(\s*['"]([^'"\n]+)['"]\s*\)""")
JS_IMPORT_STMT_RE = re.compile(r"""\bimport\s+(?:type\s+)?([^'";()]*?)\s*\bfrom\s*['"][^'"\n]+['"]""")
JS_FUNC_RE = re.compile(r'^[ \t]*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s*\*?\s*([A-Za-z_$][\w$]*)', re.M)
JS_CLASS_RE = re.compile(r'^[ \t]*(?:export\s+)?(?:default\s+)?(?:abstract\s+)?class\s+([A-Za-z_$][\w$]*)', re.M)
JS_CONST_RE = re.compile(r'^[ \t]*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*(?::[^=\n]+)?=\s*(async\s+)?(\([^)\n]*\)|[A-Za-z_$][\w$]*)?\s*(=>)?', re.M)
PY_CONST_RE = re.compile(r'^[A-Z][A-Z0-9_]*$')
JAVA_TYPE_RE = re.compile(r'\b(class|interface|enum|record)\s+(\w+)')
JAVA_METHOD_RE = re.compile(r'(?:public|protected|private)\s+(?:static\s+)?(?:final\s+)?(?:abstract\s+)?(?:synchronized\s+)?[\w<>\[\],?.]+\s+(\w+)\s*\([^)]*\)\s*(?:throws\s+[\w.,\s]+)?[{;]')
# Allows export/API macros between the keyword and the name (`class TINYXML2_LIB XMLDocument`,
# Unreal's `class MYGAME_API AMyActor : public AActor`).
CPP_TYPE_RE = re.compile(r'\b(class|struct)\s+(?:[A-Z][A-Z0-9_]*\s+)*(\w+)\s*(?:final\s*)?[:{]')
CPP_FUNC_RE = re.compile(r'^[ \t]*(?:[\w:<>*&~,]+[ \t*&]+)+([\w:~]+)\s*\([^;{}()]*\)\s*(?:const\s*)?(?:noexcept\s*)?(?:override\s*)?\{', re.M)
CPP_SKIP = {'if', 'for', 'while', 'switch', 'return', 'catch', 'else', 'sizeof'}


def blank_comments(code: str) -> str:
    """Remove // and /* */ comments but keep newlines so line numbers stay valid."""
    code = re.sub(r'/\*.*?\*/', lambda m: re.sub(r'[^\n]', ' ', m.group(0)), code, flags=re.DOTALL)
    return re.sub(r'//[^\n]*', '', code)


def line_of(text: str, pos: int) -> int:
    return text.count('\n', 0, pos) + 1


def compute_file_hash(filepath: str) -> str:
    try:
        with open(filepath, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]
    except Exception:
        return ''

def normalize_rel_path(filepath: str, root: str) -> str:
    return os.path.relpath(filepath, root).replace('\\', '/')

def atomic_write(path: str, text: str):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    temp_path = f"{path}.tmp.{os.getpid()}"
    try:
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(text)
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

def load_summarizer():
    """Load summarize() from graph-summary.py (hyphenated name, so via importlib)."""
    try:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'graph-summary.py')
        spec = importlib.util.spec_from_file_location('graph_summary', p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.summarize
    except Exception:
        return None


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
        if self.existing_graph.get('meta', {}).get('cache_version') != CACHE_VERSION:
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

    # ---------------- parsers (each returns node data incl. 'raw' imports) ----------------

    def parse_python(self, filepath: str, rel_path: str) -> Optional[Dict[str, Any]]:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        try:
            tree = ast.parse(source, filename=filepath)
        except (SyntaxError, ValueError, RecursionError, MemoryError):
            return None

        mod = rel_path.removesuffix('.py').replace('/', '.')
        classes = []
        functions = []
        imports = []
        file_edges = []
        raw = []
        symbols = []
        imported_names = []

        for top in tree.body:
            if isinstance(top, (ast.FunctionDef, ast.AsyncFunctionDef)):
                symbols.append({'name': top.name, 'kind': 'function', 'line': top.lineno})
            elif isinstance(top, ast.ClassDef):
                symbols.append({'name': top.name, 'kind': 'class', 'line': top.lineno})
                for item in top.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        symbols.append({'name': f"{top.name}.{item.name}", 'kind': 'method', 'line': item.lineno})
            elif isinstance(top, (ast.Assign, ast.AnnAssign)):
                targets = top.targets if isinstance(top, ast.Assign) else [top.target]
                for t in targets:
                    if isinstance(t, ast.Name) and PY_CONST_RE.match(t.id):
                        symbols.append({'name': t.id, 'kind': 'const', 'line': top.lineno})

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
                    raw.append({'spec': alias.name, 'level': 0, 'names': []})

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
                for a in node.names:
                    if a.name != '*' and a.name not in imported_names:
                        imported_names.append(a.name)
                if node.module or node.level:
                    raw.append({'spec': node.module or '', 'level': node.level or 0,
                                'names': [a.name for a in node.names]})

        return {
            'type': 'python',
            'path': rel_path,
            'module': mod,
            'classes': classes,
            'functions': functions,
            'imports': imports,
            'raw': raw,
            'edges': file_edges,
            'symbols': symbols,
            'imported_names': imported_names,
        }

    def parse_java(self, filepath: str, rel_path: str) -> Optional[Dict[str, Any]]:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            code = f.read()

        clean = re.sub(r'//.*', '', code)
        clean = re.sub(r'/\*.*?\*/', '', clean, flags=re.DOTALL)

        pkg_match = re.search(r'package\s+([\w\.]+);', clean)
        pkg = pkg_match.group(1) if pkg_match else 'default'

        imports = re.findall(r'import\s+([\w\.\*]+);', clean)
        file_edges = []
        raw = [{'spec': imp, 'level': 0, 'names': []} for imp in imports]

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

        symbols = []
        sclean = blank_comments(code)
        types = [(m.start(), m.group(2), m.group(1)) for m in JAVA_TYPE_RE.finditer(sclean)]
        for pos, name, kind in types:
            symbols.append({'name': name, 'kind': 'class' if kind == 'record' else kind, 'line': line_of(sclean, pos)})
        for m in JAVA_METHOD_RE.finditer(sclean):
            if m.group(1) in ('if', 'for', 'while', 'switch', 'catch'):
                continue
            owner = None
            for pos, name, _k in types:
                if pos < m.start():
                    owner = name
            nm = f"{owner}.{m.group(1)}" if owner else m.group(1)
            symbols.append({'name': nm, 'kind': 'method', 'line': line_of(sclean, m.start(1))})

        return {
            'type': 'java',
            'path': rel_path,
            'package': pkg,
            'classes': classes,
            'methods': methods,
            'imports': imports,
            'raw': raw,
            'edges': file_edges,
            'symbols': symbols,
            'imported_names': [],
        }

    def parse_cpp(self, filepath: str, rel_path: str) -> Optional[Dict[str, Any]]:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            code = f.read()

        clean = re.sub(r'//.*', '', code)
        clean = re.sub(r'/\*.*?\*/', '', clean, flags=re.DOTALL)

        includes = re.findall(r'#include\s+["<]([\w\./\\]+)[">]', clean)
        file_edges = []
        raw = [{'spec': inc, 'level': 0, 'names': []} for inc in includes]

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

        symbols = []
        sclean = blank_comments(code)
        for m in CPP_TYPE_RE.finditer(sclean):
            symbols.append({'name': m.group(2), 'kind': m.group(1), 'line': line_of(sclean, m.start(2))})
        for m in CPP_FUNC_RE.finditer(sclean):
            nm = m.group(1)
            if nm.split('::')[-1] in CPP_SKIP:
                continue
            symbols.append({'name': nm, 'kind': 'function', 'line': line_of(sclean, m.start(1))})

        return {
            'type': 'cpp',
            'path': rel_path,
            'classes': classes,
            'methods': methods[:15],
            'includes': includes,
            'raw': raw,
            'edges': file_edges,
            'symbols': symbols,
            'imported_names': [],
        }

    def parse_js(self, filepath: str, rel_path: str, lang: str) -> Optional[Dict[str, Any]]:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            code = f.read()
        specs: List[str] = []
        for rx in (JS_FROM_RE, JS_BARE_RE, JS_REQ_RE, JS_DYN_RE):
            for m in rx.finditer(code):
                if m.group(1) not in specs:
                    specs.append(m.group(1))
        classes = [{'name': n} for n in re.findall(r'\bclass\s+([A-Za-z_$][\w$]*)', code)][:15]
        symbols = []
        for m in JS_FUNC_RE.finditer(code):
            symbols.append({'name': m.group(1), 'kind': 'function', 'line': line_of(code, m.start(1))})
        for m in JS_CLASS_RE.finditer(code):
            symbols.append({'name': m.group(1), 'kind': 'class', 'line': line_of(code, m.start(1))})
        for m in JS_CONST_RE.finditer(code):
            is_exported = 'export' in code[m.start():m.start(1)]
            is_arrow = bool(m.group(4))
            if is_exported or is_arrow:
                symbols.append({'name': m.group(1), 'kind': 'function' if is_arrow else 'const',
                                'line': line_of(code, m.start(1))})
        symbols.sort(key=lambda s: s['line'])
        imported_names: List[str] = []
        for m in JS_IMPORT_STMT_RE.finditer(code):
            clause = m.group(1)
            brace = re.search(r'\{([^}]*)\}', clause)
            if brace:
                for part in brace.group(1).split(','):
                    part = re.sub(r'^\s*type\s+', '', part.strip())
                    nm = part.split(' as ')[0].strip()
                    if nm and nm not in imported_names:
                        imported_names.append(nm)
            default = clause.split('{')[0].strip().rstrip(',').strip()
            if default and re.match(r'^[A-Za-z_$][\w$]*$', default) and default not in imported_names:
                imported_names.append(default)
        return {
            'type': lang,
            'path': rel_path,
            'classes': classes,
            'imports': specs,
            'raw': [{'spec': sp, 'level': 0, 'names': []} for sp in specs],
            'edges': [],
            'symbols': symbols,
            'imported_names': imported_names,
        }

    # ---------------- resolution: raw import -> repo file(s) ----------------

    @staticmethod
    def _resolve_python(rel_path, r, files):
        d = os.path.dirname(rel_path)
        spec, level = r['spec'], r['level']
        parts = spec.split('.') if spec else []
        if level:
            base = d
            for _ in range(level - 1):
                base = os.path.dirname(base)
            bases = [base]
        else:
            # try repo root, then the importer's directory and its ancestors (script-dir imports)
            bases = []
            cur = d
            while True:
                bases.append(cur)
                if not cur:
                    break
                cur = os.path.dirname(cur)
        found = []
        for base in bases:
            def j(ps):
                return '/'.join(x for x in [base] + list(ps) if x)
            hit = False
            if parts:
                mp = j(parts)
                for cand in (mp + '.py', mp + '/__init__.py'):
                    if cand in files:
                        found.append(cand)
                        hit = True
                        break
            for n in r['names']:
                mp = j(parts + [n])
                for cand in (mp + '.py', mp + '/__init__.py'):
                    if cand in files:
                        found.append(cand)
                        hit = True
                        break
            if hit:
                break
        return found

    @staticmethod
    def _resolve_java(rel_path, r, files):
        spec = r['spec']
        if spec.endswith('.*'):
            return []
        parts = spec.split('.')
        while len(parts) >= 2:
            suffix = '/'.join(parts) + '.java'
            for f in files:
                if f == suffix or f.endswith('/' + suffix):
                    return [f]
            parts = parts[:-1]  # inner class / static member import
        return []

    @staticmethod
    def _resolve_cpp(rel_path, r, files):
        inc = r['spec'].replace('\\', '/')
        cur = os.path.dirname(rel_path)
        while True:
            cand = os.path.normpath('/'.join(x for x in (cur, inc) if x)).replace('\\', '/')
            if cand in files:
                return [cand]
            if not cur:
                break
            cur = os.path.dirname(cur)
        for pre in ('include', 'src'):
            cand = pre + '/' + inc
            if cand in files:
                return [cand]
        return []

    @staticmethod
    def _resolve_js(rel_path, r, files):
        spec = r['spec']
        if not (spec.startswith('./') or spec.startswith('../') or spec in ('.', '..')):
            return []
        target = os.path.normpath(os.path.join(os.path.dirname(rel_path), spec)).replace('\\', '/')
        if target.startswith('..'):
            return []
        if target in files and os.path.splitext(target)[1].lower() in SUPPORTED_EXTENSIONS:
            return [target]
        bases = [target]
        stem, ext = os.path.splitext(target)
        if ext.lower() in ('.js', '.jsx', '.mjs', '.cjs'):
            bases.append(stem)  # TS ESM style: './b.js' means b.ts
        for b in bases:
            for e in JS_EXTS:
                if b + e in files:
                    return [b + e]
        for e in JS_EXTS:
            cand = ('index' + e) if target == '.' else (target + '/index' + e)
            if cand in files:
                return [cand]
        return []

    @staticmethod
    def _external_name(lang, spec):
        if lang == 'python':
            return spec.split('.')[0] or None
        if lang in ('javascript', 'typescript'):
            if spec.startswith('.'):
                return None
            sp = spec.split('/')
            return '/'.join(sp[:2]) if spec.startswith('@') else sp[0]
        if lang == 'java':
            return '.'.join(spec.split('.')[:3])
        return spec

    def resolve_edges(self):
        files = set(self.nodes.keys())
        resolvers = {
            'python': self._resolve_python,
            'java': self._resolve_java,
            'cpp': self._resolve_cpp,
            'javascript': self._resolve_js,
            'typescript': self._resolve_js,
        }
        seen = set()
        edges = []
        external = defaultdict(int)
        for rel_path, node in self.nodes.items():
            lang = node.get('type')
            relation = 'includes' if lang == 'cpp' else 'imports'
            resolver = resolvers.get(lang)
            if not resolver:
                continue
            ext_seen = set()
            for r in node.get('raw', []):
                targets = resolver(rel_path, r, files)
                if targets:
                    for t in targets:
                        if t == rel_path:
                            continue
                        key = (rel_path, t, relation)
                        if key not in seen:
                            seen.add(key)
                            edges.append({'from': rel_path, 'to': t, 'relation': relation})
                elif r['level'] == 0:
                    name = self._external_name(lang, r['spec'])
                    if name and name not in ext_seen:
                        ext_seen.add(name)
                        external[name] += 1
        return edges, dict(sorted(external.items(), key=lambda kv: (-kv[1], kv[0]))[:30])

    # ---------------- build ----------------

    def build(self):
        self.load_cache()
        cached_nodes = self.existing_graph.get('nodes', {})
        files = self.find_source_files()

        reparsed_count = 0

        for filepath in files:
            rel_path = normalize_rel_path(filepath, self.root)
            current_hash = compute_file_hash(filepath)

            # Check incremental cache
            if rel_path in cached_nodes and cached_nodes[rel_path].get('hash') == current_hash:
                self.nodes[rel_path] = cached_nodes[rel_path]
                continue

            ext = os.path.splitext(filepath)[1].lower()
            lang = SUPPORTED_EXTENSIONS.get(ext)
            res = None
            try:
                if lang == 'python':
                    res = self.parse_python(filepath, rel_path)
                elif lang == 'java':
                    res = self.parse_java(filepath, rel_path)
                elif lang == 'cpp':
                    res = self.parse_cpp(filepath, rel_path)
                elif lang in ('javascript', 'typescript'):
                    res = self.parse_js(filepath, rel_path, lang)
            except Exception:  # one odd file must never abort the whole index
                res = None

            if res:
                res['hash'] = current_hash
                self.nodes[rel_path] = res
                reparsed_count += 1

        # Internal edges only (resolved against the set of repo files)
        self.edges, external = self.resolve_edges()
        in_degree = defaultdict(int)
        for e in self.edges:
            in_degree[e['to']] += 1
        self.hub_scores = dict(sorted(in_degree.items(), key=lambda x: (-x[1], x[0])))

        communities = defaultdict(list)
        for rel_path in self.nodes.keys():
            top = rel_path.split('/')[0] if '/' in rel_path else 'root'
            communities[top].append(rel_path)

        coverage: Dict[str, Dict[str, Any]] = {}
        for node in self.nodes.values():
            lang = node.get('type', 'unknown')
            c = coverage.setdefault(lang, {'files': 0, 'parser': 'ast' if lang == 'python' else 'regex'})
            c['files'] += 1

        graph_data = {
            'meta': {
                'total_files': len(self.nodes),
                'total_edges': len(self.edges),
                'reparsed_files': reparsed_count,
                'cache_version': CACHE_VERSION,
                'coverage': coverage,
                'external_modules': external,
            },
            'hub_nodes': list(self.hub_scores.items())[:12],
            'communities': dict(communities),
            'nodes': self.nodes,
            'edges': self.edges,
        }

        atomic_write(self.output_path, json.dumps(graph_data, indent=2))

        summarize = load_summarizer()
        if summarize:
            lines = summarize(graph_data, brief=True, max_lines=BRIEF_MAX_LINES)
            brief_path = os.path.join(os.path.dirname(self.output_path), 'graph-brief.txt')
            atomic_write(brief_path, '\n'.join(lines) + '\n')

        self.log(f"God Mode Graph: {len(self.nodes)} files indexed ({reparsed_count} re-parsed), {len(self.edges)} internal edges.")

def main():
    root = '.'
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
