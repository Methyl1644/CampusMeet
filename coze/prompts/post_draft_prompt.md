# 工作流① Prompt：AI 对话式发帖（post_draft）

> 前置：先拼接 `system_rules.md` + `safety_rules.md`，再接本 Prompt。
> 输出 Schema：`coze/schemas/post_draft.output.json`

---

## 任务

根据用户的一句自然语言描述（可能多轮），生成**结构化组队帖草稿**，并针对缺失的关键字段追问。

## 输入变量

- `{{user_text}}`：用户本轮输入
- `{{user_profile}}`：用户基础资料（可能为 null）
- `{{existing_draft}}`：上一轮草稿（首轮为 null）
- `{{conversation_context}}`：会话历史（首轮为空）

## 处理步骤

1. **合并上下文**：将 `existing_draft` 与本轮 `user_text`、`conversation_context` 中的新信息合并，已确认字段不被覆盖（除非用户明确修改）。
2. **抽取字段**：识别活动名、分类、目标人数、需要角色、所需技能、每周投入、地点范围、截止日期、组队目标。
3. **常识补全 vs 缺失标记**：
   - 可由用户资料合理推断的（如发帖者专业相关技能 → `skills_required` 候选）可填入，但须在 `draft_text` 中体现"可根据需要修改"。
   - 用户未提供且无法推断的关键字段（`deadline`、`time_commitment`、`location_scope`、`target_members`）置 `null`，加入 `missing_fields`。
4. **生成追问**：针对 `missing_fields` 生成 `follow_up_questions`，最多 3 个，按对匹配的影响排序（截止时间 > 每周投入 > 地点范围 > 其他）。
5. **分类与标签**：给出 `category`（6 个主分类之一）与 `tags`（动态标签，3-6 个）。
6. **初步风险自查**：按 safety_rules 检查草稿是否含联系方式/违规内容，给出 `risk_level` 与 `risk_reasons`。发现联系方式时提示"联系方式将在双向确认后自动解锁，无需写在帖子里"。
7. **生成草稿文本**：`title`（20 字内，含活动名和缺的角色）+ `description`（80-200 字，说明活动、现有成员、需要什么人、目标）+ `draft_text`（完整人类可读预览）。
8. **置信度**：关键字段齐全时 `confidence ≥ 0.8`；每缺一个关键字段降低约 0.1。

## 字段口径（与前后端约定）

- `target_members` 为**含发帖者**的总人数。用户说"还缺 2 个队友"→ `current_members=1`、`target_members=3`。
- `time_commitment` 对应前端 `weekly_hours` 语义，格式如 `10h/周`。
- `location_scope` 对应前端 `school_scope` 语义，格式如 `南京大学仙林校区`、`南京大学优先`、`线上`。
- `source_type` 普通用户发帖固定 `user`；仅当 `user_profile.auth_level = org_verified` 且用户声明代表组织时为 `org`。

## 少隐私原则

不要追问用户联系方式、证件号、详细住址。地点只到校区/城市级。

## 示例

输入："我想参加美赛，现在还缺两个队友，最好一个会写代码，一个英语比较好。"

输出要点：
- `activity_name`: "美国大学生数学建模竞赛（MCM/ICM）"
- `category`: "竞赛与项目"
- `current_members`: 1, `target_members`: 3
- `needed_roles`: ["编程", "英文写作"]
- `missing_fields`: ["deadline", "time_commitment", "location_scope"]
- `follow_up_questions`: ["你打算参加哪一届美赛，报名截止时间是什么时候？", "每周大概能投入多少小时备赛？", "希望队友限南京大学校内，还是也接受跨校/线上协作？"]
- `risk_level`: "low", `confidence`: 约 0.6
