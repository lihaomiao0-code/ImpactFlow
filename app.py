from __future__ import annotations

from textwrap import dedent
from typing import Dict, List, Tuple

import streamlit as st

from analysis_service import build_analysis_payload
from repository_loader import load_repository_from_directory, load_repository_from_zip
from reporting import build_report


st.set_page_config(
    page_title='ImpactFlow｜AI 代码变更影响分析平台',
    page_icon='⚡',
    layout='wide',
    initial_sidebar_state='expanded',
)

SAMPLE_SOURCES = {
    'src/utils/math_ops.py': dedent('''
        def normalize(values):
            return [v / max(values) for v in values]


        def safe_average(values):
            normalized = normalize(values)
            return sum(normalized) / len(normalized)
    ''').strip(),
    'src/services/risk_service.py': dedent('''
        from src.utils.math_ops import normalize, safe_average


        def compute_risk(values):
            score = safe_average(values)
            return score ** 0.5
    ''').strip(),
    'src/api/report_api.py': dedent('''
        from src.services.risk_service import compute_risk


        def render_report(values):
            risk = compute_risk(values)
            return f"risk={risk:.3f}"
    ''').strip(),
}

PRD_SECTIONS = [
    ('产品定位', '面向研发团队的代码变更影响分析平台，聚焦 PR 审查、发布前检查与回归风险控制。'),
    ('目标用户', '开发工程师、Reviewer、测试工程师、技术负责人。'),
    ('核心能力', '仓库接入、代码解析、diff 识别、影响传播、风险评估、建议生成、报告输出。'),
    ('阶段规划', 'MVP 聚焦 Python 仓库分析；V1 增加 Git 与历史记录；V2 覆盖多语言与 AI 自动补丁。'),
]

SAMPLE_DIFFS = {
    'src/utils/math_ops.py': dedent('''
        @@ -1,6 +1,6 @@
         def normalize(values):
        -    return [v / max(values) for v in values]
        +    return [v / (max(values) or 1) for v in values]
    ''').strip(),
}

APP_CSS = '''
<style>
    :root {
        --bg: #0b1020;
        --panel: rgba(17, 24, 39, 0.78);
        --panel-strong: rgba(15, 23, 42, 0.92);
        --border: rgba(148, 163, 184, 0.15);
        --text: #e5e7eb;
        --muted: #94a3b8;
        --primary: #7c3aed;
        --primary-2: #22c55e;
        --warning: #f59e0b;
        --danger: #ef4444;
    }
    .stApp {
        background:
            radial-gradient(circle at top left, rgba(124,58,237,0.24), transparent 35%),
            radial-gradient(circle at top right, rgba(34,197,94,0.18), transparent 30%),
            linear-gradient(180deg, #050816 0%, #0b1020 40%, #111827 100%);
        color: var(--text);
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(15,23,42,0.98), rgba(9,14,28,0.98));
        border-right: 1px solid var(--border);
    }
    .hero {
        padding: 1.8rem 2rem;
        border-radius: 24px;
        background: linear-gradient(135deg, rgba(124,58,237,0.18), rgba(59,130,246,0.10));
        border: 1px solid var(--border);
        box-shadow: 0 20px 60px rgba(0,0,0,0.25);
        margin-bottom: 1.2rem;
    }
    .hero h1 {
        margin: 0;
        font-size: 2rem;
        line-height: 1.2;
    }
    .hero p {
        margin-top: 0.7rem;
        color: var(--muted);
        max-width: 52rem;
        font-size: 0.98rem;
    }
    .panel {
        padding: 1.2rem 1.2rem 0.9rem;
        border-radius: 20px;
        background: var(--panel);
        border: 1px solid var(--border);
        box-shadow: 0 12px 35px rgba(0,0,0,0.16);
        margin-bottom: 1rem;
    }
    .stat {
        padding: 1rem 1rem;
        border-radius: 18px;
        background: linear-gradient(180deg, rgba(15,23,42,0.85), rgba(17,24,39,0.72));
        border: 1px solid var(--border);
    }
    .label { color: var(--muted); font-size: 0.84rem; }
    .value { font-size: 1.6rem; font-weight: 700; margin-top: 0.25rem; }
    .subtle { color: var(--muted); }
    .tag {
        display: inline-block;
        padding: 0.35rem 0.65rem;
        border-radius: 999px;
        background: rgba(124,58,237,0.14);
        border: 1px solid rgba(124,58,237,0.25);
        color: #ddd6fe;
        margin-right: 0.4rem;
        margin-bottom: 0.4rem;
        font-size: 0.82rem;
    }
    .badge {
        display: inline-block;
        padding: 0.24rem 0.55rem;
        border-radius: 999px;
        font-size: 0.75rem;
        margin-right: 0.4rem;
        color: white;
    }
    .badge-low { background: rgba(34,197,94,0.22); border: 1px solid rgba(34,197,94,0.35); }
    .badge-medium { background: rgba(245,158,11,0.22); border: 1px solid rgba(245,158,11,0.35); }
    .badge-high { background: rgba(239,68,68,0.22); border: 1px solid rgba(239,68,68,0.35); }
    .badge-roadmap { background: rgba(59,130,246,0.22); border: 1px solid rgba(59,130,246,0.35); }
</style>
'''

st.markdown(APP_CSS, unsafe_allow_html=True)

PRD_SECTIONS: List[Tuple[str, str]] = [
    ('产品定位', '面向研发团队的代码变更影响分析平台，自动识别改动、评估传播范围并输出风险与建议。'),
    ('目标用户', '开发工程师、Reviewer、测试工程师与技术负责人。'),
    ('核心能力', '仓库接入、代码解析、变更识别、影响传播、风险评估、建议生成、报告输出。'),
    ('里程碑', 'MVP 聚焦仓库导入与影响分析，V1 增加历史记录与 Git 集成，V2 增强多语言与 LLM 能力。'),
]

ROADMAP_ITEMS = [
    ('MVP', '仓库导入、Python 解析、diff 识别、影响分析、建议生成、报告展示'),
    ('V1', 'Git 仓库接入、历史记录、版本对比、风险规则配置、Markdown / PDF 导出'),
    ('V2', '多语言支持、LLM 生成补丁、CI/CD 集成、团队协作、权限控制、风险预测'),
]

if 'repo_files' not in st.session_state:
    st.session_state.repo_files = SAMPLE_SOURCES.copy()
if 'repo_diffs' not in st.session_state:
    st.session_state.repo_diffs = SAMPLE_DIFFS.copy()
if 'repo_name' not in st.session_state:
    st.session_state.repo_name = 'sample-repo'
if 'last_payload' not in st.session_state:
    st.session_state.last_payload = None

with st.sidebar:
    st.markdown('## ImpactFlow')
    st.caption('AI 代码变更影响分析平台')
    mode = st.radio('工作模式', ['仓库扫描', '手动编辑'], index=0)
    st.markdown('---')
    uploaded_zip = st.file_uploader('上传 ZIP 仓库', type=['zip'])
    uploaded_folder = st.text_input('或填写本地仓库路径', placeholder='/path/to/repository')
    st.markdown('---')
    st.markdown('### 产品能力')
    st.write('• 仓库扫描与静态分析')
    st.write('• 变更影响面识别')
    st.write('• 自动修复建议')
    st.write('• 测试补全建议')
    st.write('• PR / 发布前风险摘要')
    analyze_button = st.button('开始分析', use_container_width=True)

st.markdown(
    '''
    <div class="hero">
        <span class="tag">AI Repository Intelligence</span>
        <span class="tag">Impact Analysis</span>
        <span class="tag">Auto Repair Guidance</span>
        <h1>面向研发团队的 AI 变更影响分析平台</h1>
        <p>支持上传整个仓库、自动抽取依赖关系、评估变更风险并生成修复补丁与测试建议，帮助团队在 PR 审查和发布前降低回归风险。</p>
    </div>
    ''',
    unsafe_allow_html=True,
)


def _risk_badge(level: str) -> str:
    mapping = {
        '低风险': 'badge-low',
        '中风险': 'badge-medium',
        '高风险': 'badge-high',
        '严重风险': 'badge-high',
    }
    cls = mapping.get(level, 'badge-medium')
    return f"<span class='badge {cls}'>{level}</span>"


def render_metrics(payload: Dict):
    cols = st.columns(5)
    values = [
        ('文件数', payload['summary']['files']),
        ('函数数', payload['summary']['functions']),
        ('变更函数', payload['summary']['changed_functions']),
        ('影响函数', payload['summary']['impacted_functions']),
        ('依赖边数', payload['summary']['edges']),
    ]
    for col, (label, value) in zip(cols, values):
        with col:
            st.markdown(f"<div class='stat'><div class='label'>{label}</div><div class='value'>{value}</div></div>", unsafe_allow_html=True)


def render_result(payload: Dict):
    render_metrics(payload)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader('产品定位与路线图')
    top_cols = st.columns([0.55, 0.45], gap='large')
    risk_level = payload['summary'].get('risk_level', '中风险')
    risk_score = payload['summary'].get('risk_score', 0)
    with top_cols[0]:
        st.markdown(
            f"{_risk_badge(risk_level)} <span class='badge badge-medium'>PR 审查</span> "
            f"<span class='badge badge-roadmap'>发布前检查</span>",
            unsafe_allow_html=True,
        )
        st.write(f'当前风险评分：{risk_score}/100，系统会根据变更函数与传播范围自动评估。')
    with top_cols[1]:
        for stage, desc in ROADMAP_ITEMS:
            st.markdown(f"<div class='tag'>{stage}</div>", unsafe_allow_html=True)
            st.write(desc)
    st.markdown('</div>', unsafe_allow_html=True)

    left, right = st.columns([0.56, 0.44], gap='large')
    with left:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader('影响分析')
        st.markdown(build_report(payload['sources'], payload['diffs']))
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader('自动修复补丁建议')
        for item in payload['patch_hints']:
            st.write(f'• {item}')
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader('测试建议')
        for item in payload['test_hints']:
            st.write(f'• {item}')
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader('产品 PRD 概览')
        for title, desc in PRD_SECTIONS:
            st.markdown(f"<div class='tag'>{title}</div>", unsafe_allow_html=True)
            st.write(desc)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader('仓库概览')
        if payload['repo_summary']:
            for ext, count in sorted(payload['repo_summary'].items(), key=lambda x: (-x[1], x[0])):
                st.write(f'• `{ext}`：{count} 个文件')
        else:
            st.info('没有可分析的源代码文件')
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader('变更函数')
        if payload['changed']:
            for item in payload['changed']:
                st.write(f"• `{item['qualified_name']}`")
        else:
            st.info('未识别到变更函数')
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader('受影响范围')
        if payload['impacted']:
            for item in payload['impacted']:
                st.write(f"• `{item['name']}` — {item['reason']}")
        else:
            st.info('暂无下游影响')
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader('关联建议')
    if payload['related']:
        for item in payload['related']:
            st.write(f"• `{item['name']}` 相关度 {item['score']:.2f}")
    else:
        st.info('暂无可展示的关联建议')
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader('工程化落地建议')
    st.write('• 将分析结果接入 PR/CI，在合并前自动生成风险摘要')
    st.write('• 支持版本对比、历史追踪和修复建议回溯')
    st.write('• 将自动补丁建议与测试建议做成可执行任务流')
    st.write('• 后续可接入 LLM，形成“分析—生成—验证—回收”的闭环')
    st.markdown('</div>', unsafe_allow_html=True)


if analyze_button or mode == '手动编辑':
    if uploaded_zip is not None:
        snapshot = load_repository_from_zip(uploaded_zip.getvalue(), uploaded_zip.name)
        st.session_state.repo_files = snapshot.files
        st.session_state.repo_name = snapshot.root
    elif uploaded_folder:
        snapshot = load_repository_from_directory(uploaded_folder)
        st.session_state.repo_files = snapshot.files
        st.session_state.repo_name = snapshot.root

    if mode == '手动编辑' and not st.session_state.repo_files:
        st.session_state.repo_files = SAMPLE_SOURCES.copy()

    with st.expander('查看当前仓库文件', expanded=False):
        st.write(f"当前仓库：{st.session_state.repo_name}")
        st.json(list(st.session_state.repo_files.keys()))

    if mode == '手动编辑':
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader('编辑样例仓库')
        source_math = st.text_area('`src/utils/math_ops.py`', value=st.session_state.repo_files.get('src/utils/math_ops.py', SAMPLE_SOURCES['src/utils/math_ops.py']), height=180)
        source_risk = st.text_area('`src/services/risk_service.py`', value=st.session_state.repo_files.get('src/services/risk_service.py', SAMPLE_SOURCES['src/services/risk_service.py']), height=150)
        source_api = st.text_area('`src/api/report_api.py`', value=st.session_state.repo_files.get('src/api/report_api.py', SAMPLE_SOURCES['src/api/report_api.py']), height=150)
        st.markdown('</div>', unsafe_allow_html=True)
        st.session_state.repo_files = {
            'src/utils/math_ops.py': source_math,
            'src/services/risk_service.py': source_risk,
            'src/api/report_api.py': source_api,
        }

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader('提交 diff')
    diff_math = st.text_area('`src/utils/math_ops.py` diff', value=st.session_state.repo_diffs.get('src/utils/math_ops.py', SAMPLE_DIFFS['src/utils/math_ops.py']), height=220)
    st.markdown('</div>', unsafe_allow_html=True)
    st.session_state.repo_diffs = {'src/utils/math_ops.py': diff_math}

    payload = build_analysis_payload(st.session_state.repo_files, st.session_state.repo_diffs)
    st.session_state.last_payload = payload
    render_result(payload)
else:
    payload = build_analysis_payload(st.session_state.repo_files, st.session_state.repo_diffs)
    render_result(payload)

st.markdown('<div class="panel">', unsafe_allow_html=True)
st.subheader('核心逻辑')
logic_col1, logic_col2, logic_col3 = st.columns(3)
with logic_col1:
    st.write('1. 扫描 ZIP 或本地仓库，抽取可解析源文件')
    st.write('2. 基于 AST 构建函数级依赖图')
with logic_col2:
    st.write('3. 基于 diff 定位变更函数与影响范围')
    st.write('4. 生成自动修复与测试建议')
with logic_col3:
    st.write('5. 为 PR/CI 提供可视化审查和风险摘要')
    st.write('6. 为后续 LLM 代码补丁闭环预留接口')
st.markdown('</div>', unsafe_allow_html=True)
