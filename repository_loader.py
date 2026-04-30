from __future__ import annotations

import io
import os
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


SUPPORTED_EXTENSIONS = {
    '.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.go', '.rb', '.php', '.rs', '.cs'
}


@dataclass
class RepositorySnapshot:
    root: str
    files: Dict[str, str]
    detected_language: str


def _is_hidden(path: Path) -> bool:
    return any(part.startswith('.') for part in path.parts)


def _should_include(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS and not _is_hidden(path)


def _detect_language(files: Iterable[str]) -> str:
    suffix_rank = {}
    for file_path in files:
        suffix = Path(file_path).suffix.lower()
        suffix_rank[suffix] = suffix_rank.get(suffix, 0) + 1
    if not suffix_rank:
        return 'unknown'
    top = max(suffix_rank.items(), key=lambda item: item[1])[0]
    mapping = {
        '.py': 'Python',
        '.ts': 'TypeScript',
        '.tsx': 'TypeScript React',
        '.js': 'JavaScript',
        '.jsx': 'JavaScript React',
        '.java': 'Java',
        '.go': 'Go',
        '.rb': 'Ruby',
        '.php': 'PHP',
        '.rs': 'Rust',
        '.cs': 'C#',
    }
    return mapping.get(top, top.lstrip('.') or 'unknown')


def load_repository_from_directory(root_path: str) -> RepositorySnapshot:
    root = Path(root_path)
    files: Dict[str, str] = {}
    for file_path in root.rglob('*'):
        if file_path.is_file() and _should_include(file_path.relative_to(root)):
            try:
                files[file_path.relative_to(root).as_posix()] = file_path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                continue
    return RepositorySnapshot(root=root.as_posix(), files=files, detected_language=_detect_language(files.keys()))


def load_repository_from_zip(uploaded_bytes: bytes, filename: str = 'repository.zip') -> RepositorySnapshot:
    with tempfile.TemporaryDirectory() as tmp_dir:
        archive_path = Path(tmp_dir) / filename
        archive_path.write_bytes(uploaded_bytes)
        extract_root = Path(tmp_dir) / 'extracted'
        extract_root.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(uploaded_bytes)) as zf:
            zf.extractall(extract_root)

        candidate_root = extract_root
        children = [path for path in extract_root.iterdir() if path.is_dir()]
        if len(children) == 1:
            candidate_root = children[0]

        files: Dict[str, str] = {}
        for file_path in candidate_root.rglob('*'):
            if file_path.is_file() and _should_include(file_path.relative_to(candidate_root)):
                try:
                    files[file_path.relative_to(candidate_root).as_posix()] = file_path.read_text(encoding='utf-8')
                except UnicodeDecodeError:
                    continue
        return RepositorySnapshot(root=candidate_root.as_posix(), files=files, detected_language=_detect_language(files.keys()))


def summarize_repository(files: Dict[str, str]) -> Dict[str, int]:
    by_extension: Dict[str, int] = {}
    for path in files:
        suffix = Path(path).suffix.lower() or '<no-ext>'
        by_extension[suffix] = by_extension.get(suffix, 0) + 1
    return by_extension
