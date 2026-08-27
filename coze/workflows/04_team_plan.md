# 工作流④：成队规划（team-plan）

| 项 | 内容 |
|----|------|
| 工作流名（Coze 后台） | `campusmate_team_plan` |
| 对应后端工具 | `ai_team_plan`（`src/tools/ai_tools.py`） |
| 对应前端页面 | 成队成功页 / 团队详情页 `/teams/:id`（P0，对应功能 F12） |
| 环境变量 | `COZE_WORKFLOW_TEAM_PLAN_ID` |
| 输入 Schema | `coze/schemas/team_plan.input.json` |
| 输出 Schema | `coze/schemas/team_plan.output.json` |
| Prompt | `coze/prompts/team_plan_prompt.md`（前置拼接 `system_rules.md` + `safety_rules.md`） |
| 优先级 | P0 |

## 1. 目标

双向确认成队后自动生成：建议分工、第一次会议议程、第一周任务清单、里程碑、风险提醒。**只建议不决定**，成员可自行调整（user-flow §3 阶段七）。

## 2. 触发时机

```
双方均点击"愿意组队" → 后端创建团队 → 解锁联系方式 → 异步调用 ai_team_plan
→ 结果写入团队记录 → 成队页展示分工/议程/任务/风险
```

## 3. 工作流画布设计（Coze 节点）

```
[开始] → [输入校验+日期推算(代码节点)] → [LLM: 规划生成] → [输出校验(代码节点)] → [结束]
                                                    │
                                                    └─ 异常 → [兜底输出] → [结束]
```

| 节点 | 类型 | 说明 |
|------|------|------|
| 开始 | Start | 输入：`team_info`、`activity_info`、`members`、`deadline`、`member_skills`、`member_availability` |
| 输入校验+日期推算 | Code | 校验 members ≥ 2、member_skills/availability 的 key 与 members 的 user_id 对齐；注入 `current_date` 供任务排期；校验 `deadline` 日期格式 |
| LLM：规划生成 | LLM | System = system_rules + safety_rules + team_plan_prompt；JSON 输出 |
| 输出校验 | Code | 校验：`role_assignments` 覆盖全部 members；`first_week_tasks` 每条 owner_id ∈ members 且 due ≤ deadline（若 deadline 存在）；议程 ≥ 3 项；risk_reminders ≥ 1 条 |
| 兜底输出 | Code | LLM 失败时输出模板化兜底：每人一个"待定"角色 + 通用议程（确认目标/分工/时间表）+ 1 条截止提醒；后端同时提示"暂时无法生成规划建议，团队已创建成功"（user-flow §4.1） |
| 结束 | End | 输出 7 个字段 |

## 4. 校验规则细节

- `first_week_tasks[].owner_id` 必须是 `members` 中的 user_id，否则改派给技能最匹配的成员。
- `first_week_tasks[].due` 若晚于 `deadline`，强制提前到 deadline 前一天。
- `missing_roles` 非空时，`risk_reminders` 必须包含能力缺口提醒（校验节点自动补一条）。
- 所有日期统一 `YYYY-MM-DD`。

## 5. 异常处理

| 异常 | 行为 |
|------|------|
| LLM 超时/失败 | 兜底输出 + 后端提示，团队创建不受阻 |
| members 与 skills 对不齐 | 缺 skills 的成员按"通用成员"处理，reason 注明"技能信息待补充" |
| deadline 为 null | 任务排期以 current_date + 7 天为界，risk_reminders 提示"关键截止日期未设置，建议团队确认" |
| 未配置工作流 ID | 后端切 LLM fallback |

## 6. 测试样例

| 场景 | 输入摘要 | 期望 | 评测集 |
|------|---------|------|--------|
| 美赛三人队 | 小王+小李+小张，截止 08-15 | 分工与技能匹配、任务含负责人和截止日期 | `evals/team_plan_cases.jsonl` case-01 |
| 角色缺口 | 两人队缺论文写作 | missing_roles 非空 + 风险提醒 | case-04 |
| 投入不均 | 一人 4h/周 | 不给其压重任务 + 风险提醒 | case-05 |
| 无截止日期 | deadline=null | 提示需确认截止 | case-08 |
