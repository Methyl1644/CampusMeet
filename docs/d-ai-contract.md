# CampusMate AI 成员 D 接口契约与交接说明

> 状态：2026-09-02 已与 B 的共享类型、C 的 FastAPI 路由对账完成。
> 原则：前端只依赖稳定 JSON，不关心结果来自 Coze 还是 fallback；真实 Token 和 workflow ID 只放本地 `.env`。

## 1. 统一响应外壳

C 的 `/api/*` 路由统一返回：

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

AI 工具内部可以带 `success`、`message` 或 `team_plan`。C 在 `src/api/agent.py` 负责拆包，B 只读取 `data`。

## 2. 四个 AI 接口

### 2.1 对话式发帖

`POST /api/agent/post-draft`

```json
{
  "message": "我想参加美赛，还缺两个队友。",
  "draft": null,
  "user_skills": ["Python", "数学建模"],
  "kind": "topic_team",
  "topic_id": "12",
  "field_states": {}
}
```

`data` 至少包含 `reply/draft/is_complete/field_states/suggested_tag_ids`。草稿使用 `activity_name/target_members/needed_roles/weekly_hours/school_scope/deadline/description`。路由会从数据库生成 `candidate_tags` 并把前端对象/数组转换为工具参数；Coze 只能返回候选列表中的标准标签 ID。

### 2.2 分类与审核

`POST /api/agent/classify-review`

```json
{
  "title": "美赛队伍招募编程和英文写作队友",
  "description": "已有一名成员，希望再招两人。"
}
```

后端会额外注入 `candidate_tags`。`data` 固定为 `main_category/tag_ids/unknown_concepts/risk_level/suggestions`。`tag_ids` 只能来自标准候选；`unknown_concepts` 只进入待审核队列，不会自动成为标签。路由会在调用 Coze 前使用规则引擎脱敏；发布、拦截和人工审核的最终决定权在后端。

### 2.3 队友匹配

`POST /api/agent/match`

```json
{
  "post_id": "1"
}
```

`data` 为 `{"matches": [{"user_id": "2", "score": 87, "reason": "技能与目标匹配"}]}`。后端先查询可见候选人，排除帖主、拉黑用户和受限账号，然后只向 Coze 发送候选编号、昵称、专业、年级和公开技能。返回编号必须属于该候选集，分数会被限制在 0-100，重复和越权结果会被丢弃。

### 2.4 成队规划

`POST /api/agent/team-plan`

```json
{
  "team_id": "1"
}
```

`data` 固定为 `division_of_labor/meeting_agenda/task_list/risk_reminders`。后端只发送当前成员的公开技能和已批准职责，并校验分工中的成员编号、任务去重及字段长度。无论使用部署 API、旧工作流或 fallback，通过校验的计划都会写回 `teams` 表。

## 3. Coze 与 fallback 切换

```text
COZE_DEPLOY_API_TOKEN
COZE_POST_DRAFT_API_URL
COZE_CLASSIFY_REVIEW_API_URL
COZE_MATCH_API_URL
COZE_TEAM_PLAN_API_URL

# 旧版后备
COZE_WORKFLOW_POST_DRAFT
COZE_WORKFLOW_CLASSIFY_REVIEW
COZE_WORKFLOW_MATCH
COZE_WORKFLOW_TEAM_PLAN
```

1. 同时配置 `COZE_DEPLOY_API_TOKEN` 和对应 `.coze.site/run` 地址时优先调用 Coze 部署 API。
2. 新接口失败时尝试旧版 `COZE_API_TOKEN + COZE_WORKFLOW_*`；仍失败才进入 fallback。
3. 发帖/审核使用 LLM fallback；匹配/规划使用数据库受控上下文 + LLM 或确定性 fallback。
4. 密码、验证码、原始身份材料和未脱敏联系方式禁止发给 Coze。

## 4. Git 交接

D 修改应从最新 `main` 创建 `feat/d-*` 分支，提交后向团队集成分支发 PR。任何 AI 契约改动都要同步更新 `packages/shared/src/types.ts`、`src/api/agent.py`、`coze/schemas/` 和本文档，并重跑 `tests/test_d_ai_fallback.py`。
