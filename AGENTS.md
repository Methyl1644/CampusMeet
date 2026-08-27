# AGENTS.md

## 项目概述

CampusMate AI：面向高校学生的可信 AI 组队平台（不是普通论坛）。核心闭环：官方活动发现 → AI 需求整理 → 结构化组队帖 → 分类审核 → 队友匹配 → 申请沟通 → 双向确认成队 → AI 成队规划。

团队分工：A=产品文档（已完成，见 `docs/`）、B=前端（React+Vite，`apps/web` + `packages/shared`，**代码尚未推送到仓库**）、C=后端与安全（FastAPI + LangGraph + 安全规则引擎，**业务代码尚未推送到仓库**）、D=智能体与算法（Coze 工作流/Prompt/Schema/评测集，交付物在 `coze/`）。

## 技术栈

- 后端：Python 3.12 + FastAPI + LangGraph + SQLAlchemy，`uv` 管理依赖（`pyproject.toml` / `uv.lock`）
- 前端（未到位）：React 18 + Vite + TypeScript + Tailwind + Zustand + Axios
- 智能体：Coze 工作流（4 个 P0 工作流 + 1 个 P1），后端通过 `src/tools/ai_tools.py` 调用，未配置工作流 ID 时走 LLM fallback

## 目录结构

- `docs/`：A 的产品文档（prd / user-flow / pages / demo-script / test-cases / review-notes），**契约权威来源**
- `src/`：后端。当前仓库内只有 Coze LangGraph 模板脚手架（`main.py` 为通用 graph 运行时，`storage/` 为模板基础设施）；C 的业务代码（`tools/ai_tools.py`、`utils/security.py`、`agents/agent.py`、8 张业务表）尚未推送
- `coze/`：D 的交付物。`workflows/` 工作流设计、`prompts/` 提示词、`schemas/` 输入输出 JSON Schema、`evals/` 评测集（JSONL）、`examples/` 演示数据、`INTEGRATION.md` 集成说明
- `scripts/`：模板自带的运行脚本（setup / http_run / local_run / pack）

## 关键入口 / 核心模块

- `docs/prd.md` §5-6：分类体系（6 个主分类）、安全规则、帖子/申请数据结构——所有 schema 的字段以此为准
- `docs/user-flow.md` §3：AI 发帖草稿字段（activity_name / target_members / needed_roles / weekly_hours / school_scope）与匹配输出示例（score / hard_conflicts / reasons / reminders）
- `docs/demo-script.md`：小王美赛演示故事线（评测集与 examples 的场景来源）
- `coze/INTEGRATION.md`：Coze 工作流 ↔ 后端工具 ↔ 环境变量的对接总表，含待 B/C 代码到位后的对账清单

## 运行与预览

- `project_type = "backend"`，不可预览（preview_enable = disabled）
- 运行：`bash scripts/setup.sh` 后 `bash scripts/http_run.sh`（模板 HTTP 服务，入口 `src/main.py`）
- 环境：Python 3.12 + uv 虚拟环境；数据库连接走 `PGDATABASE_URL`

## 用户偏好与长期约束

- 团队仓库：<https://github.com/Methyl1644/EL_CampusMate>，协作分支约定见 README（dev 开发、main 发布）
- D 的任务边界：不重写前端、不重写后端主体、不大规模重构已有业务逻辑；schema 优先兼容前后端现有约定
- Coze 数据边界（PRD §5.3）：密码、原始身份证明、脱敏前联系方式不发送给 Coze

## 常见问题和预防

- **B/C 代码未推送**：当前仓库无 `apps/web`、`packages/shared`、`src/tools/ai_tools.py` 等。凡涉及前后端字段契约的内容，以 `docs/` + 任务说明字段清单为准，并在 `coze/INTEGRATION.md` 的"待对账清单"登记，代码到位后逐条核对
- 评测集 JSONL 每行必须是合法 JSON，修改后用 `python -m json.tool` 逐行校验
