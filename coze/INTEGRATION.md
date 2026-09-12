# INTEGRATION.md — Coze 工作流 ↔ 后端 ↔ 前端 对接说明

> 读者：成员 C（后端接入）为主，B（前端）和答辩演示负责人参考。
> 目标：C 拿到 Coze 工作流 ID 后能在 30 分钟内完成接入；答辩时能按本文档展示每个工作流的试运行。
> 应用层实际请求/响应以 `docs/d-ai-contract.md` 为联调标准；丰富 Coze Schema 只作为工作流内部推理结构。

---

## 1. 工作流清单与用途

| # | 工作流 | Coze 后台名称 | 用途 | 优先级 |
|---|--------|--------------|------|--------|
| ① | post-draft | `campusmate_post_draft` | 需求拆解、逐项追问、标准标签推荐 | P0 |
| ② | classify-review | `campusmate_classify_review` | 标准标签推荐、库外概念提案、风险初筛 | P0 |
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

当前后端直接透传的 Coze 入参为：post-draft 的 `message/draft/user_skills/kind/field_states/candidate_tags/topic_id`，classify-review 的 `title/description/candidate_tags`，match-teammates 的 `post_id`，team-plan 的 `team_id`。前两项的权威契约是对应 `schemas/*.json`，不得继续使用旧字段 `user_text/post_draft/raw_text/dynamic_tags`。

前端触点：

| 前端接口 / 页面 | 工作流 | 说明 |
|----------------|--------|------|
| `POST /api/agent/post-draft` | ① | 发布页 AI 对话式发帖 |
| `POST /api/agent/classify-review` | ② | 帖子提交后自动触发 |
| 首页"为你推荐"、帖子详情页匹配度 | ③ | 匹配分数 + 理由展示 |
| 成队页 `/teams/:id` | ④ | 双向确认后自动触发 |

## 3. 环境变量配置

`.env` 中推荐配置部署 API（`.env.example` 已有占位）：

```bash
# Token 只放后端，前端不持有任何 Token（PRD §7）
COZE_DEPLOY_API_TOKEN=<部署页生成的 API Token>
COZE_POST_DRAFT_API_URL=https://<deployment>.coze.site/run
COZE_CLASSIFY_REVIEW_API_URL=
```

配置步骤：

1. 前两个工作流先按 `DELIVERY_CHECKLIST.md` 和 `workflows/01_*.md`、`02_*.md` 搭建；
2. LLM 节点的 System Prompt = `prompts/system_rules.md` + `prompts/safety_rules.md` + 对应任务 Prompt（三段拼接）；
3. 发布工作流，复制 `/run` API 地址并生成 API Token；
4. 把 Token 和地址填入 Render 后重启后端，`ai_tools.py` 自动切换到 Coze 部署 API。

旧版 `COZE_API_TOKEN`、`COZE_API_BASE_URL` 和 `COZE_WORKFLOW_*` 仍可作为后备配置。

## 4. Coze 不可用时的 LLM fallback

后端 `ai_tools.py` 的每个 AI 工具是**双层架构**：

```
if 对应 COZE_*_API_URL 和 COZE_DEPLOY_API_TOKEN 已配置:
    调用 Coze 部署 API（超时/异常 → 尝试旧版工作流）
elif 对应 COZE_WORKFLOW_* 已配置:
    调用旧版 Coze 工作流
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

## 7. B/C/D 对账结果（2026-09-02）

> B 的 `packages/shared`/`apps/web` 和 C 的 `src/api`/`src/tools` 已在 `main` 上传。D 已按实际代码完成静态对账，并用 `tests/test_d_ai_fallback.py` 覆盖四工具的 Coze 切换与 fallback。

| # | 对账项 | 实际结论 | 状态 / 确认人 |
|---|--------|-------------|-----------------|
| 1 | post-draft 请求 | B 传 `message/draft/user_skills`；C 在路由层序列化对象和数组后调 D 工具 | ✅ B/C/D |
| 2 | post-draft 响应 | 应用层固定 `reply/draft/is_complete`，路由统一包装 `{code,message,data}` | ✅ B/C/D |
| 3 | 草稿字段名 | 正式字段为 `weekly_hours/school_scope`；Coze 内部别名需在入口/出口映射 | ✅ D |
| 4 | 主分类枚举 | B 共享类型与 D Prompt 均使用六个中文主分类 | ✅ B/D |
| 5 | 风险等级 | 应用层统一 `low/medium/high`；最终发布/拦截由 C 的规则引擎决定 | ✅ C/D |
| 6 | 敏感信息 | C 在 classify-review 路由中先脱敏，D/Coze 不接收未脱敏联系方式 | ✅ C/D |
| 7 | 匹配入参/响应 | 入参固定 `post_id`；C 返回 `data.matches`；B 使用 `MatchResponse` 和 `user_id/score/reason` | ✅ B/C/D |
| 8 | 环境变量 | 优先使用 `COZE_DEPLOY_API_TOKEN + COZE_*_API_URL`；旧版 `COZE_WORKFLOW_*` 保留后备；真实 Token 只放后端环境 | ✅ C/D |
| 9 | team-plan 响应 | C 解包 `team_plan`；B 使用 `DivisionItem[]/AgendaItem[]/TaskItem[]` | ✅ B/C/D |
| 10 | fallback 行为 | 未配置 Coze 时：发帖/审核走 LLM，匹配/规划走数据库 + LLM，规划结果会入库 | ✅ D 自动化实测 |

实测命令和结果见 `docs/d-fallback-test-report.md`。若后续真正开启 `COZE_WORKFLOW_MATCH`，还必须先实现工作流中的受控上下文查询节点。
