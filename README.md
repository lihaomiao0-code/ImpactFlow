# AI 代码变更影响分析平台

一个基于 Cursor Agent 工作流思路构建的多文件代码变更影响分析原型。项目围绕“变更定位、影响传播、风险提示、修复建议”四个核心能力展开，适合作为 AI 驱动研发提效类项目 Demo。

## 功能特性

- 多文件 AST 静态分析
- 导入与调用关系推导
- Git diff 变更行定位
- 受影响范围反向传播
- 结构化分析报告
- 产品化风格的 Streamlit 界面

## 运行方式

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 项目结构

- `app.py`：Streamlit 前端页面
- `analyzer.py`：代码解析与影响分析核心逻辑
- `analysis_service.py`：面向 UI 的分析数据封装
- `reporting.py`：Markdown 报告输出
- `models.py`：数据结构定义

## 产品文档

- `PRD.md`：正式产品需求文档，定义了产品定位、目标用户、核心功能与迭代规划

## 后续可扩展方向

- 支持目录级批量导入
- 支持 Python 以外的多语言解析
- 接入 LLM 生成自动修复补丁
- 增加 PR 审查报告导出
- 集成单测执行与 CI/CD 流程
