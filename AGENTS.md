# AGENTS.md

## 项目概述

CampusMate AI：面向高校学生的可信 AI 组队平台（不是普通论坛）。核心闭环：官方活动发现 → AI 需求整理 → 结构化组队帖 → 分类审核 → 队友匹配 → 申请沟通 → 双向确认成队 → AI 成队规划。

团队分工：A=产品文档（见 `docs/`）、B=前端（React+Vite，`apps/web` + `packages/shared`）、C=后端与安全（FastAPI + LangGraph + 安全规则引擎，`src/`）、D=智能体与算法（Coze 工作流/Prompt/Schema/评测集，`coze/`）。

> **当前状态（2026-08-29）**：A/B/C/D 四方交付物均已推送到 main。当前唯一阻塞项是**前后端协议未对接**——前端调 `/api/*` REST 接口，后端 `src/main.py` 是 Coze 模板 runtime（只有 `/run` `/stream_run`），没有 `/api/*` 路由。解决方案见 `docs/api-alignment.md`，核心是新增 `src/api.py` 路由层把 tool 包装成 REST 接口。

## 技术栈

- 后端：Python 3.12 + FastAPI + LangGraph + SQLAlchemy，`uv` 管理依赖（`pyproject.toml` / `uv.lock`）。Windows 开发需先从 `pyproject.toml` 删除 `pycairo` / `dbus-python` / `PyGObject` 三个 Linux 专属依赖（业务代码未使用）。
- 前端：React 18 + Vite + TypeScript + Tailwind + Zustand + Axios，`apps/web`
- 智能体：Coze 工作流（4 个 P0 + 1 个 P1），后端通过 `src/tools/ai_tools.py` 调用，未配置工作流 ID 时走 LLM fallback

## 目录结构

- `docs/`：A 的产品文档（prd / user-flow / pages / demo-script / test-cases / review-notes），**契约权威来源**
- `src/`：后端。`main.py` 为 FastAPI 入口，`api.py` 为 `/api/*` REST 路由层（接前端），`tools/` 为业务工具，`agents/agent.py` 为 LangGraph agent 定义（当前演示路径不走 agent，走 REST 路由直调 tool）
- `coze/`：D 的交付物。`workflows/` 工作流设计、`prompts/` 提示词、`schemas/` 输入输出 JSON Schema、`evals/` 评测集（JSONL）、`examples/` 演示数据、`INTEGRATION.md` 集成说明
- `scripts/`：`setup.sh` / `http_run.sh` 为 Coze 模板自带运行脚本；`seed.py` 为演示数据灌入脚本

## 关键入口 / 核心模块

- `docs/prd.md` §5-6：分类体系（6 个主分类）、安全规则、帖子/申请数据结构——所有 schema 的字段以此为准
- `docs/user-flow.md` §3：AI 发帖草稿字段（activity_name / target_members / needed_roles / weekly_hours / school_scope）与匹配输出示例（score / hard_conflicts / reasons / reminders）
- `docs/demo-script.md`：小王美赛演示故事线（评测集与 examples 的场景来源）
- `coze/INTEGRATION.md`：Coze 工作流 ↔ 后端工具 ↔ 环境变量的对接总表，含待 B/C 代码到位后的对账清单

## 运行与预览

- 后端：`python src/main.py -m http -p 3000`（端口 3000，前端 vite 已把 `/api` 代理到此）
- 环境：Python 3.12；数据库连接走环境变量 `DATABASE_URL`（**不是** `PGDATABASE_URL`，`db.py` 已兼容两者但优先读 `DATABASE_URL`）
- 首次启动自动建表；建表后跑 `python scripts/seed.py` 灌入演示数据

## 用户偏好与长期约束

- 团队仓库：<https://github.com/Methyl1644/EL_CampusMate>，协作分支约定见 README（dev 开发、main 发布）
- D 的任务边界：不重写前端、不重写后端主体、不大规模重构已有业务逻辑；schema 优先兼容前后端现有约定
- Coze 数据边界（PRD §5.3）：密码、原始身份证明、脱敏前联系方式不发送给 Coze

## 常见问题和预防

- **Windows 装包失败**：`pyproject.toml` 含 `pycairo` / `dbus-python` / `PyGObject` 三个 Linux 专属依赖，Windows 上装不上。删除这三行后 `pip install -e .` 即可。
- **前后端协议**：前端走 `/api/*` REST（见 `packages/shared/src/constants.ts`），后端 `src/api.py` 提供对应路由。字段对账见 `docs/api-alignment.md`。
- 评测集 JSONL 每行必须是合法 JSON，修改后用 `python -m json.tool` 逐行校验
