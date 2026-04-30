from typing import Dict, List

from analyzer import analyze_files, find_changed_functions_in_files, match_similarity, suggest_impacted_functions


def build_report(sources: Dict[str, str], diffs: Dict[str, str]) -> str:
    analysis = analyze_files(sources)
    changed = find_changed_functions_in_files(sources, diffs)
    impacted = suggest_impacted_functions(analysis, changed)
    impacted_names = [name for name, _ in impacted]
    top_related = match_similarity(' '.join(fn.qualified_name for fn in changed), impacted_names)

    lines: List[str] = [
        '### 分析结果',
        '',
        '#### 变更函数',
    ]
    if changed:
        for fn in changed:
            lines.append(f'- `{fn.qualified_name}` ({fn.module}:{fn.start_line}-{fn.end_line})')
    else:
        lines.append('- 未检测到变更函数')

    lines.extend(['', '#### 受影响范围'])
    if impacted:
        for name, reason in impacted:
            lines.append(f'- `{name}`: {reason}')
    else:
        lines.append('- 暂无可推导的下游影响')

    lines.extend(['', '#### 相似关联建议'])
    if top_related:
        for name, score in top_related[:5]:
            lines.append(f'- `{name}` 相关度 {score:.2f}')
    else:
        lines.append('- 无')

    lines.extend([
        '',
        '#### 自动建议',
        '- 为变更函数补充单元测试',
        '- 检查上游调用者是否需要同步调整',
        '- 运行 lint 与类型检查以确认无回归',
    ])
    return '\n'.join(lines)
