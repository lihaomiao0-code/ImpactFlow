import ast
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import networkx as nx

from models import CodebaseAnalysis, FileNode, FunctionNode


class MultiFileCodeAnalyzer(ast.NodeVisitor):
    def __init__(self, module_name: str):
        self.module_name = module_name
        self.functions: Dict[str, FunctionNode] = {}
        self.import_aliases: Dict[str, str] = {}
        self._current_function: Optional[FunctionNode] = None

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            target = alias.name.split('.')[0]
            self.import_aliases[alias.asname or target] = alias.name

    def visit_ImportFrom(self, node: ast.ImportFrom):
        module = node.module or ''
        for alias in node.names:
            alias_name = alias.asname or alias.name
            qualified = f'{module}.{alias.name}'.strip('.')
            self.import_aliases[alias_name] = qualified

    def visit_FunctionDef(self, node: ast.FunctionDef):
        qualified_name = f'{self.module_name}.{node.name}' if self.module_name else node.name
        fn = FunctionNode(
            name=node.name,
            qualified_name=qualified_name,
            module=self.module_name,
            start_line=node.lineno,
            end_line=getattr(node, 'end_lineno', node.lineno),
        )
        previous = self._current_function
        self._current_function = fn
        self.functions[qualified_name] = fn
        self.generic_visit(node)
        self._current_function = previous

    def visit_ClassDef(self, node: ast.ClassDef):
        previous_function = self._current_function
        for child in node.body:
            self.visit(child)
        self._current_function = previous_function

    def visit_Call(self, node: ast.Call):
        if self._current_function is not None:
            call_name = self._resolve_call_name(node.func)
            if call_name:
                self._current_function.calls.add(call_name)
        self.generic_visit(node)

    def _resolve_call_name(self, node: ast.AST) -> Optional[str]:
        if isinstance(node, ast.Name):
            return self.import_aliases.get(node.id, node.id)
        if isinstance(node, ast.Attribute):
            base = self._resolve_call_name(node.value)
            if base:
                return f'{base}.{node.attr}'
            return node.attr
        return None


def module_name_from_path(path: str) -> str:
    return Path(path).with_suffix('').as_posix().replace('/', '.')


def analyze_files(sources: Dict[str, str]) -> CodebaseAnalysis:
    file_nodes: Dict[str, FileNode] = {}
    all_functions: Dict[str, FunctionNode] = {}
    graph = nx.DiGraph()
    source_lines: Dict[str, List[str]] = {}

    for path, source in sources.items():
        module_name = module_name_from_path(path)
        tree = ast.parse(source)
        analyzer = MultiFileCodeAnalyzer(module_name)
        analyzer.visit(tree)
        source_lines[path] = source.splitlines()

        file_nodes[path] = FileNode(path=path, source=source, functions=analyzer.functions)
        for fn_name, fn in analyzer.functions.items():
            all_functions[fn_name] = fn
            graph.add_node(fn_name, label=fn_name, module=fn.module, start=fn.start_line, end=fn.end_line)

    for fn in all_functions.values():
        for call in fn.calls:
            for target_name in all_functions.keys():
                if target_name.endswith(f'.{call}') or target_name == call:
                    graph.add_edge(fn.qualified_name, target_name)

    return CodebaseAnalysis(graph=graph, files=file_nodes, functions=all_functions, source_lines=source_lines)


def extract_changed_lines(diff_text: str) -> Set[int]:
    changed_lines: Set[int] = set()
    current_line = 0
    for raw_line in diff_text.splitlines():
        if raw_line.startswith('@@'):
            parts = raw_line.split(' ')
            if len(parts) >= 3:
                new_chunk = parts[2]
                start = int(new_chunk.split(',')[0][1:])
                current_line = start - 1
            continue
        if raw_line.startswith('+') and not raw_line.startswith('+++'):
            current_line += 1
            changed_lines.add(current_line)
        elif raw_line.startswith('-') and not raw_line.startswith('---'):
            continue
        else:
            current_line += 1
    return changed_lines


def find_changed_functions(source: str, diff_text: str, path: str = 'app.py') -> List[FunctionNode]:
    analysis = analyze_files({path: source})
    changed_lines = extract_changed_lines(diff_text)
    changed: List[FunctionNode] = []
    for fn in analysis.functions.values():
        if any(fn.start_line <= line <= fn.end_line for line in changed_lines):
            changed.append(fn)
    return changed


def find_changed_functions_in_files(sources: Dict[str, str], diffs: Dict[str, str]) -> List[FunctionNode]:
    analysis = analyze_files(sources)
    changed: List[FunctionNode] = []
    for path, diff_text in diffs.items():
        changed_lines = extract_changed_lines(diff_text)
        for fn in analysis.files.get(path, FileNode(path, '', {})).functions.values():
            if any(fn.start_line <= line <= fn.end_line for line in changed_lines):
                changed.append(fn)
    return changed


def suggest_impacted_functions(analysis: CodebaseAnalysis, changed: List[FunctionNode]) -> List[Tuple[str, str]]:
    impacted: List[Tuple[str, str]] = []
    reverse_graph = analysis.graph.reverse(copy=False)
    queue = [fn.qualified_name for fn in changed]
    visited = set(queue)

    while queue:
        current = queue.pop(0)
        for parent in reverse_graph.neighbors(current):
            if parent not in visited:
                visited.add(parent)
                queue.append(parent)
                impacted.append((parent, f'{parent} 调用了受影响函数 {current}'))
    return impacted


def match_similarity(query: str, candidates: List[str]) -> List[Tuple[str, float]]:
    scored = [(candidate, SequenceMatcher(None, query.lower(), candidate.lower()).ratio()) for candidate in candidates]
    return sorted(scored, key=lambda item: item[1], reverse=True)
