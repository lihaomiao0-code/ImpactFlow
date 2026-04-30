from dataclasses import dataclass, field
from typing import Dict, List, Set

import networkx as nx


@dataclass
class FunctionNode:
    name: str
    qualified_name: str
    module: str
    start_line: int
    end_line: int
    calls: Set[str] = field(default_factory=set)


@dataclass
class FileNode:
    path: str
    source: str
    functions: Dict[str, FunctionNode]


@dataclass
class CodebaseAnalysis:
    graph: nx.DiGraph
    files: Dict[str, FileNode]
    functions: Dict[str, FunctionNode]
    source_lines: Dict[str, List[str]]
