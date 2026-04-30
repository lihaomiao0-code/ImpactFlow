from dataclasses import asdict
from typing import Any, Dict, List, Optional

from analyzer import analyze_files, find_changed_functions_in_files, match_similarity, suggest_impacted_functions
from repository_loader import RepositorySnapshot, summarize_repository


DEFAULT_REPAIR_HINTS = [
    '为变更函数补充单元测试和边界条件测试',
    '检查所有上游调用方，确认参数/返回值契约未破坏',
    '补充回归测试，覆盖影响链上所有关键路径',
    '在 PR 审查中附带影响分析报告与修复建议',
]


def _compute_risk_score(changed_count: int, impacted_count: int, settings: Dict[str, Any]) -> int:
    base = changed_count * 18 + impacted_count * 12
    if changed_count >= settings.get('high_change_threshold', 2):
        base += 10
    if impacted_count >= settings.get('high_impacted_threshold', 3):
        base += 15
    if settings.get('severity_boost', True):
        base += 8 if impacted_count else 0
    return min(100, base)


def _risk_level_from_score(score: int) -> str:
    if score < 25:
        return '低风险'
    if score < 55:
        return '中风险'
    if score < 80:
        return '高风险'
    return '严重风险'


def _infer_test_suggestions(changed_functions: List[Any], impacted: List[Any]) -> List[str]:
    suggestions = []
    for fn in changed_functions:
        suggestions.append(f'创建 `{fn.module}` 对应的单元测试，覆盖 `{fn.name}` 的正常/异常/边界场景')
    if impacted:
        suggestions.append('补充集成测试，覆盖受影响调用链的端到端行为')
    suggestions.extend(DEFAULT_REPAIR_HINTS)
    deduped = []
    for item in suggestions:
        if item not in deduped:
            deduped.append(item)
    return deduped[:8]


def _generate_patch_hints(changed_functions: List[Any], impacted: List[Any]) -> List[str]:
    hints = []
    for fn in changed_functions:
        hints.append(f'优先在 `{fn.module}` 中保留兼容性封装，减少外部调用方改动')
        hints.append(f'对 `{fn.qualified_name}` 增加输入校验和空值保护')
    for item in impacted[:3]:
        hints.append(f'同步审查 `{item[0]}` 的调用契约，避免链式回归')
    deduped = []
    for item in hints:
        if item not in deduped:
            deduped.append(item)
    return deduped[:8]


def _calculate_risk_score(changed_count: int, impacted_count: int, edge_count: int, function_count: int) -> int:
    score = 15
    score += min(changed_count * 18, 36)
    score += min(impacted_count * 8, 32)
    score += min(edge_count // 2, 12)
    if function_count > 0:
        score += min((impacted_count * 100) // function_count, 15)
    return max(0, min(score, 100))


def _risk_level(score: int) -> str:
    if score >= 75:
        return '严重风险'
    if score >= 50:
        return '高风险'
    if score >= 25:
        return '中风险'
    return '低风险'


def build_analysis_payload(
    sources: Dict[str, str],
    diffs: Dict[str, str],
    risk_settings: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    analysis = analyze_files(sources)
    changed = find_changed_functions_in_files(sources, diffs)
    impacted = suggest_impacted_functions(analysis, changed)
    impacted_names = [name for name, _ in impacted]
    top_related = match_similarity(' '.join(fn.qualified_name for fn in changed), impacted_names)
    repo_summary = summarize_repository(sources)
    settings = risk_settings or {}

    graph_nodes = []
    for node, attrs in analysis.graph.nodes(data=True):
        graph_nodes.append({'id': node, **attrs})

    graph_edges = []
    for source, target in analysis.graph.edges():
        graph_edges.append({'source': source, 'target': target})

    risk_score = _compute_risk_score(len(changed), len(impacted), settings)
    risk_level = _risk_level_from_score(risk_score)
    severity_score = 8 if impacted and settings.get('severity_boost', True) else 0

    return {
        'summary': {
            'files': len(sources),
            'functions': len(analysis.functions),
            'changed_functions': len(changed),
            'impacted_functions': len(impacted),
            'edges': len(graph_edges),
            'risk_score': risk_score,
            'risk_level': risk_level,
            'risk_profile': {
                'change_score': len(changed) * 18,
                'impact_score': len(impacted) * 12,
                'severity_score': severity_score,
            },
        },
        'repo_summary': repo_summary,
        'changed': [asdict(fn) for fn in changed],
        'impacted': [{'name': name, 'reason': reason} for name, reason in impacted],
        'related': [{'name': name, 'score': score} for name, score in top_related[:5]],
        'patch_hints': _generate_patch_hints(changed, impacted),
        'test_hints': _infer_test_suggestions(changed, impacted),
        'graph': {'nodes': graph_nodes, 'edges': graph_edges},
        'sources': sources,
        'diffs': diffs,
    }
