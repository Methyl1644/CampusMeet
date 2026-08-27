# 工作流③ Prompt：智能匹配（match_teammates）

> 前置：先拼接 `system_rules.md` + `safety_rules.md`，再接本 Prompt。
> 输出 Schema：`coze/schemas/match_teammates.output.json`
> 核心要求：**可解释**。禁止只输出"匹配度 92%"这类没有依据的分数。

---

## 任务

对候选队友逐个评估，输出匹配分数、可接受性、推荐理由、潜在风险和建议沟通问题。

## 输入变量

- `{{post_requirements}}`：帖子组队需求
- `{{candidate_profiles}}`：候选人列表（已脱敏）
- `{{current_team_members}}`：现有成员
- `{{hard_filters}}`：硬筛选条件

## 第一层：确定性筛选（硬条件）

对每位候选人依次检查，命中任意一条 → `acceptability = not_recommended`，`score ≤ 30`，冲突写入 `hard_conflicts`：

1. **时间冲突**：候选人每周投入明显低于帖子要求（如要求 10h/周，候选人 4h/周）
2. **地点不可接受**：`hard_filters.location_required` 有值且候选人地点不符，又不接受线上
3. **跨校限制**：`cross_school_allowed = false` 且候选人非本校且 `accept_cross_school` 不满足
4. **队伍无空位**：现有成员数 + 已通过候选 ≥ `max_team_size`
5. **技能不满足**：`must_have_skills` 中的技能候选人一项都不具备
6. **截止已过**：`current_date` 晚于帖子 `deadline`

## 第二层：语义匹配（软条件，仅对通过硬筛者）

从五个维度打分并合成 `score`（0-100）：

| 维度 | 权重 | 判断要点 |
|------|------|---------|
| 目标一致 | 25% | 双方目标是否一致（冲奖 vs 完成即可） |
| 能力互补 | 30% | 候选人技能是否补上 `needed_roles`，且不与现有成员重复 |
| 经验适配 | 20% | 相关经验（参赛、论文、项目）与活动层级是否匹配 |
| 投入接近 | 15% | 每周投入是否接近帖子要求 |
| 沟通兼容 | 10% | 线上/线下偏好、沟通方式是否兼容 |

## 输出要求（每位候选人）

- `matched_reasons`：≥1 条，**必须引用具体证据**（技能、经验、时间、目标），禁止"你们很合适"这类空话。示例："对方有英文论文经验，正好匹配英文写作角色"。
- `potential_risks`：如实写出不确定点，如"对方每周投入 6h，低于帖子期望的 10h"。无则 `[]`。
- `suggested_questions`：给双方 1-3 个落地沟通问题，如"是否接受每周一次线下讨论？"。
- `summary`：一句话，可直接展示在推荐卡片上。
- 结果按 `score` 降序；`conditional` 用于"硬条件无冲突但有关键信息待确认"（如地点未填）。

## 示例

输入：小王美赛帖（需编程+英文写作，10h/周，南京大学优先，目标冲奖），候选人小李（外语系，英语写作，有 EI 会议论文经验，6h/周，目标冲奖）。

输出要点：
- `score`: 87, `acceptability`: "recommended"
- `matched_reasons`: ["对方有英文会议论文经验，匹配英文写作角色", "双方目标均为冲奖", "技能与现有成员（数学建模/Python）互补"]
- `potential_risks`: ["对方每周可投入 6h，低于帖子期望的 10h"]
- `suggested_questions`: ["每周投入时间能否接近 10h？", "是否接受每周一次线下讨论？"]
