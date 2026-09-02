# 工作流③：智能匹配（match-teammates）

| 项 | 内容 |
|----|------|
| 工作流名（Coze 后台） | `campusmate_match_teammates` |
| 对应后端工具 | `ai_match_teammates`（`src/tools/ai_tools.py`） |
| 对应前端接口 | 首页"为你推荐"与帖子详情页的匹配度/推荐理由（P1，对应功能 F13） |
| 环境变量 | `COZE_WORKFLOW_MATCH` |
| 输入 Schema | `coze/schemas/match_teammates.input.json` |
| 输出 Schema | `coze/schemas/match_teammates.output.json` |
| Prompt | `coze/prompts/match_teammates_prompt.md`（前置拼接 `system_rules.md` + `safety_rules.md`） |
| 优先级 | P1（已实现，不阻塞 P0） |

## 1. 目标

给候选队友生成匹配分数和**可解释**推荐理由：为什么推荐、哪里有风险、建议双方沟通什么。禁止只输出"匹配度 92%"。

## 2. 两层匹配架构

对外输入只有 `post_id`。后端当前会按 `{"post_id": post_id}` 调用 Coze，因此工作流需在进入两层匹配前，通过受控后端接口换取已脱敏的 `post_requirements`、`candidate_profiles`、`current_team_members` 和 `hard_filters`。该接口尚未接入时，`COZE_WORKFLOW_MATCH` 必须留空，由后端 fallback 直接查库。

```
第一层：确定性筛选（代码节点，不用 LLM）
  时间冲突 / 地点不可接受 / 跨校限制 / 队伍空位 / 必备技能 / 截止已过
        │ 通过                          │ 未通过
        ▼                                ▼
第二层：语义匹配（LLM 节点）      acceptability=not_recommended
  目标一致25% / 能力互补30% /      score≤30 + hard_conflicts
  经验适配20% / 投入接近15% /
  沟通兼容10%
        ▼
  合成 score 0-100 + reasons/risks/questions/summary
```

**设计理由**：硬条件用代码节点做确定性计算，保证可复现、可单测；LLM 只做软条件的语义判断，减少幻觉导致的"该筛掉的被推荐"。

## 3. 工作流画布设计（Coze 节点）

| 节点 | 类型 | 说明 |
|------|------|------|
| 开始 | Start | 输入：`post_id`(String) |
| 受控上下文查询 | HTTP/插件 | 使用 `post_id` 查询已脱敏的帖子需求、候选人、现有成员与硬条件；不返回联系方式、认证材料或密码 |
| 硬筛选 | Code | 逐候选人执行第一层 6 条规则；产出 `passed[]` 与 `rejected[]`（含 `hard_conflicts`） |
| LLM：语义匹配 | LLM | 仅处理 `passed[]`；System = system_rules + safety_rules + match_teammates_prompt；JSON 输出 |
| 合并与校验 | Code | 合并 passed 评分与 rejected 结果；校验 score∈[0,100]、matched_reasons≥1、按 score 降序；LLM 对某候选人失败时该候选人降级为 `conditional` + 模板化理由 |
| 结束 | End | 输出 `matches` 数组 |

## 4. 批量与性能约定

- 单次调用候选人上限 **20 人**，超出由后端先按技能标签粗筛再分批调用。
- `hard_filters.current_date` 由后端注入，保证"截止已过"判断一致。

## 5. 异常处理

| 异常 | 行为 |
|------|------|
| 候选人为空 | 直接返回 `matches: []` |
| LLM 超时/失败 | 已硬筛通过者返回 `conditional` + 基础匹配条件说明；前端提示"暂时无法生成推荐理由，可查看基础匹配条件"（user-flow §4.1） |
| 单个候选人评分异常 | 仅该候选人降级，不影响其他候选人 |
| 未配置工作流 ID / 受控查询未就绪 | 后端切 LLM + 数据库 fallback，再失败只展示基础匹配条件 |

## 6. 测试样例

| 场景 | 输入摘要 | 期望 | 评测集 |
|------|---------|------|--------|
| 小李匹配小王美赛帖 | 英文写作+EI 论文+6h/周 | score≈87、recommended、含投入不足风险提示 | `evals/match_teammates_cases.jsonl` case-01 |
| 硬冲突：已截止 | current_date 晚于 deadline | not_recommended、hard_conflicts 含"招募已截止" | case-06 |
| 硬冲突：技能不符 | 无任何必备技能 | not_recommended | case-07 |
| 有条件推荐 | 地点信息缺失 | conditional + suggested_questions 含地点确认 | case-08 |
| 多候选人排序 | 3 个候选人 | 按 score 降序 | case-15 |
