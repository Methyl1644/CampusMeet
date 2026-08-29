# INTEGRATION.md — Coze 工作流 ↔ 后端 ↔ 前端 对接说明

> 读者：成员 C（后端接入）为主，B（前端）和答辩演示负责人参考。
> 目标：C 拿到 Coze 工作流 ID 后能在 30 分钟内完成接入；答辩时能按本文档展示每个工作流的试运行。

---

## 1. 工作流清单与用途

| # | 工作流 | Coze 后台名称 | 用途 | 优先级 |
|---|--------|--------------|------|--------|
| ① | post-draft | `campusmate_post_draft` | 自然语言 → 结构化组队帖草稿 + 缺失字段追问 | P0 |
| ② | classify-review | `campusmate_classify_review` | 自动分类、打标签、风险评估、脱敏与审核建议 | P0 |
| ③ | match-teammates | `campusmate_match_teammates` | 候选队友匹配分数 + 可解释推荐理由 | P1 |
| ④ | team-plan | `campusmate_team_plan` | 成队后分工、首次会议议程、任务清单、风险提醒 | P0 |
| ⑤ | official-activity-extract | `campusmate_official_activity_extract` | 官方页面文本 → 标准活动卡（运营辅助） | P1 可选 |

各工作流的画布节点、异常处理、测试样例见 `workflows/0X_*.md`。

## 2. 工作流 ↔ 后端工具对应表

| 工作流 | 后端工具函数（`src/tools/ai_tools.py`） | 输入 Schema | 输出 Schema |
|--------|----------------------------------------|-------------|-------------|
| ① post-draft | `ai_post_draft` | `schemas/post_draft.input.json` | `schemas/post_draft.output.json` |
| ② classify-review | `ai_classify_review` | `schemas/classify_review.input.json` | `schemas/classify_review.output.json` |
| ③ match-teammates | `ai_match_teammates` | `schemas/match_teammates.input.json` | `schemas/match_teammates.output.json` |
| ④ team-plan | `ai_team_plan` | `schemas/team_plan.input.json` | `schemas/team_plan.output.json` |

前端触点：

| 前端接口 / 页面 | 工作流 | 说明 |
|----------------|--------|------|
| `POST /api/agent/post-draft` | ① | 发布页 AI 对话式发帖 |
| `POST /api/agent/classify-review` | ② | 帖子提交后自动触发 |
| 首页"为你推荐"、帖子详情页匹配度 | ③ | 匹配分数 + 理由展示 |
| 成队页 `/teams/:id` | ④ | 双向确认后自动触发 |

## 3. 环境变量配置

`.env` 中需要以下变量（`.env.example` 已有占位）：

```bash
# Coze 平台凭证（只放后端，前端不持有任何 Token —— PRD §7）
COZE_API_TOKEN=<在 Coze 后台创建的个人访问令牌>
COZE_API_BASE_URL=https://api.coze.cn

# 4 个工作流 ID（在 Coze 后台发布工作流后获得）
# 注意：变量名不带 _ID 后缀，与 src/tools/ai_tools.py 和 .env.example 一致
COZE_WORKFLOW_POST_DRAFT=
COZE_WORKFLOW_CLASSIFY_REVIEW=
COZE_WORKFLOW_MATCH=
COZE_WORKFLOW_TEAM_PLAN=

# 可选（P1）
COZE_WORKFLOW_ACTIVITY_EXTRACT=
```

配置步骤：

1. 在 Coze 平台按 `workflows/0X_*.md` 的画布设计搭建工作流；
2. LLM 节点的 System Prompt = `prompts/system_rules.md` + `prompts/safety_rules.md` + 对应任务 Prompt（三段拼接）；
3. 发布工作流，拿到 workflow ID 填入 `.env`；
4. 重启后端，`ai_tools.py` 自动切换到 Coze 工作流调用。

## 4. 未配置工作流 ID 时的 LLM fallback

后端 `ai_tools.py` 的每个 AI 工具是**双层架构**：

```
if 对应 COZE_WORKFLOW_* 已配置:
    调用 Coze 工作流（超时/异常 → 记录日志并降级）
else:
    调用 LLM fallback（同一套 Prompt + 同一个输出 Schema 直接问 LLM）
```

- fallback 使用与 Coze 工作流**完全相同**的 Prompt 文件和输出 Schema，保证两种路径行为一致；
- fallback 再失败时，按 `docs/user-flow.md` §4.1 的兜底策略：发帖给手动表单、审核进待审核队列、匹配只展示基础条件、成队规划给模板化建议——**不阻塞主流程**；
- 因此 C 可以先用 fallback 联调全链路，再逐个接入 Coze 工作流。

## 5. 数据边界：禁止发送给 Coze 的内容（PRD §5.3）

后端调用任何工作流前必须剔除 / 脱敏：

| 禁止项 | 说明 |
|--------|------|
| 密码 | 任何形态、任何字段 |
| 原始身份证明 | 身份证/学生证照片及其 OCR 文本 |
| 原始验证码 | 邮箱/手机验证码 |
| 原始认证材料 | 认证过程上传的任何材料原文（只保留认证结果） |
| 未脱敏的联系方式 | 手机号、微信、QQ——除非业务确实需要且用户已授权；帖子/聊天文本先经 `security.py` 掩码再传入 |

防御性措施：即使后端漏脱敏，工作流②的"输入校验+脱敏复查"节点会二次掩码并在 `reviewer_note` 记录（见 `prompts/safety_rules.md` §6）。

## 6. 答辩演示指引

| 演示项 | 操作 | 展示点 |
|--------|------|--------|
| Coze 工作流画布 | 打开 Coze 后台 4 个工作流 | 节点结构：输入校验 → LLM → 输出校验 → 兜底 |
| post-draft 试运行 | 在 Coze 试运行面板输入评测集 `pd-01`（小王美赛那句话） | 追问 3 个问题 + 结构化草稿 + missing_fields |
| classify-review 试运行 | 输入 `cr-01`（正常美赛帖）再输入 `cr-11`（代写帖） | 正常帖 approve；代写帖 high/reject，对比强烈 |
| match-teammates 试运行 | 输入 `mt-01`（小李 vs 小王帖子） | 87 分 + 3 条理由 + 1 条风险提示 + 建议沟通问题 |
| team-plan 试运行 | 输入 `tp-01`（美赛三人队） | 分工/议程/任务/里程碑/风险，直接对应成队页 |
| 接口对应关系 | 对照本文档 §2 表格 | Coze 工作流 ↔ `ai_tools.py` 函数 ↔ 前端接口一一对应 |
| 完整链路 | 按 `examples/demo_xiaowang_mcm.json` + `docs/demo-script.md` 演示 | 发帖 → 审核 → 匹配 → 申请 → 成队 → 规划 |

## 7. 待对账清单（B/C 代码推送后逐条核对）

> 背景：截至本文件创建时，B（前端 `packages/shared`）与 C（后端 `src/tools/ai_tools.py`、`src/utils/security.py`）的代码**尚未推送到仓库**。`schemas/` 以 `docs/` + 任务说明字段清单为基准定义。代码推送后，D 与 B/C 按本清单逐条核对，如有出入**优先调整 `coze/schemas/` 兼容现有前后端**，不改动前端 API 路径与后端工具函数名。

| # | 对账项 | 本目录的约定 | 待核对方 |
|---|--------|-------------|---------|
| 1 | `POST /api/agent/post-draft` 请求体 vs `PostDraftRequest` | `post_draft.input.json`：`user_text` 必填 + `user_profile`/`existing_draft`/`conversation_context` 可选 | B 的 `types.ts` |
| 2 | `POST /api/agent/post-draft` 响应体 vs `PostDraftResponse` | `post_draft.output.json`：20 个字段全量返回 | B 的 `types.ts` |
| 3 | 字段命名映射 | `time_commitment` 对应前端语义 `weekly_hours`；`location_scope` 对应 `school_scope`（user-flow §3.3 草稿字段用后者命名）——若前端已用 `weekly_hours`/`school_scope` 作为正式字段名，schema 需在保持后端兼容的前提下增加别名说明 | B、C |
| 4 | 主分类枚举 | 6 个主分类：竞赛与项目 / 学习与科研 / 体育与健身 / 旅行与户外 / 校园生活 / 拼团与AA（PRD §5.2） | B 的筛选常量、C 的枚举 |
| 5 | 风险等级 / 审核结论枚举 | `risk_level`: low/medium/high；`audit_result`: approve/modify/manual_review/reject | C 的 `security.py` |
| 6 | 敏感信息检测口径 | `prompts/safety_rules.md` §1 的 6 类（身份证号/手机号/微信/QQ/精确住址/违禁词）与风险升级矩阵 | C 的 `security.py` 正则与违禁词表 |
| 7 | 匹配输出字段 | `score`/`hard_conflicts`/`matched_reasons`/`potential_risks`/`suggested_questions` vs user-flow 示例的 `score`/`hard_conflicts`/`reasons`/`reminders`——字段名若以前端 `types.ts` 为准需做一次映射 | B、C |
| 8 | 环境变量名 | `COZE_API_TOKEN` / `COZE_API_BASE_URL` / 4 个 `COZE_WORKFLOW_*`（不带 `_ID` 后缀） | C 的 `.env.example` |
| 9 | fallback 行为 | 未配置 ID → LLM fallback → 再失败按 user-flow §4.1 兜底 | C 的 `ai_tools.py` 实现 |

核对完成后：在本表"待核对方"列填确认人，把结论记到 `docs/review-notes.md` 走查记录。
