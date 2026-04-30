from __future__ import annotations

from textwrap import dedent
from typing import Dict

import streamlit as st

from analysis_service import build_analysis_payload
from repository_loader import load_repository_from_directory, load_repository_from_zip
from reporting import build_report


st.set_page_config(
    page_title='AI Code Impact Cloud',
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
</style>
'''

st.markdown(APP_CSS, unsafe_allow_html=True)

if 'repo_files' not in st.session_state:
    st.session_state.repo_files = SAMPLE_SOURCES.copy()
if 'repo_diffs' not in st.session_state:
    st.session_state.repo_diffs = SAMPLE_DIFFS.copy()
if 'repo_name' not in st.session_state:
    st.session_state.repo_name = 'sample-repo'
if 'last_payload' not in st.session_state:
    st.session_state.last_payload = None

with st.sidebar:
    st.markdown('## AI Code Impact Cloud')
    st.caption('Repository intelligence for engineering teams')
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
    st.write('• SaaS 风格报告输出')
    analyze_button = st.button('开始分析', use_container_width=True)

st.markdown(
    '''
    <div class="hero">
        <span class="tag">AI Repository Intelligence</span>
        <span class="tag">Impact Analysis</span>
        <span class="tag">Auto Repair Guidance</span>
        <h1>面向中大型代码仓库的 AI 变更影响分析平台</h1>
        <p>支持上传整个仓库、自动抽取依赖关系、评估变更风险并生成修复补丁与测试建议，适合作为工程团队的 PR 审查与回归防线。</p>
    </div>
    ''',
    unsafe_allow_html=True,
)


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
