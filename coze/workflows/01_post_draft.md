# 工作流 1：需求拆解与发帖

| 配置 | 值 |
|------|----|
| Coze 名称 | `campusmate_post_draft` |
| 网站接口 | `POST /api/agent/post-draft` |
| Render 变量 | `COZE_POST_DRAFT_API_URL` |
| 输入 Schema | `coze/schemas/post_draft.input.json` |
| 输出 Schema | `coze/schemas/post_draft.output.json` |
| Prompt | `system_rules.md` + `safety_rules.md` + `post_draft_prompt.md` |

## 画布

`开始 -> 输入整理（代码） -> 草稿生成（大模型） -> 输出校验（代码） -> 结束`

异常分支：草稿生成或输出校验失败时，进入“安全兜底（代码）”，再连接结束节点。

## 节点配置

1. **开始**：按输入 Schema 创建七个变量。`message/kind/field_states/candidate_tags` 必填，其余可选。
2. **输入整理**：去除 `message` 首尾空格并限制 2000 字；确认 `kind` 枚举；将空的 `draft/user_skills/topic_id` 设为 `""`。
3. **草稿生成**：开启 JSON 输出；系统提示词按表中顺序拼接；用户消息传入开始节点的完整 JSON。
4. **输出校验**：拒绝不在状态枚举中的字段状态；过滤所有不在 `candidate_tags` 中的 `suggested_tag_ids`；去重并截断为 4 个；重新计算 `missing_fields/next_field/is_complete`。
5. **安全兜底**：保留传入的 `field_states` 与 `candidate_tags`，返回简短追问；`suggested_tag_ids=[]`、`degraded=true`，不得把模型错误原文返回给用户。
6. **结束**：输出 Schema 中九个字段逐一映射，不能把整个模型文本作为一个字符串返回。Coze 中 `next_field` 使用 String，没有下一字段时输出 `""`，由后端转换为 `null`。

## 校验节点规则

```text
allowed_ids = candidate_tags 中的 tag_id 集合
suggested_tag_ids = 模型 tag_ids 与 allowed_ids 的交集，去重，最多 4 个
missing_fields = status == "pending" 的字段名
next_field = missing_fields[0]，若为空则 ""
is_complete = missing_fields 为空
degraded = false
```

## 验收

使用 `coze/evals/post_draft_cases.jsonl` 至少试运行五例。必须覆盖首轮拆解、多轮补全、“没有”、跳过和库内标签锁定；任何输出标签 ID 都必须来自该用例的候选列表。
