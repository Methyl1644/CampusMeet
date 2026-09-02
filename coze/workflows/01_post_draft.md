# 工作流①：AI 对话式发帖（post-draft）

| 项 | 内容 |
|----|------|
| 工作流名（Coze 后台） | `campusmate_post_draft` |
| 对应后端工具 | `ai_post_draft`（`src/tools/ai_tools.py`） |
| 对应前端接口 | `POST /api/agent/post-draft` |
| 环境变量 | `COZE_WORKFLOW_POST_DRAFT` |
| 输入 Schema | `coze/schemas/post_draft.input.json` |
| 输出 Schema | `coze/schemas/post_draft.output.json` |
| Prompt | `coze/prompts/post_draft_prompt.md`（前置拼接 `system_rules.md` + `safety_rules.md`） |
| 优先级 | P0（对应功能 F03） |

## 1. 目标

用户输入一句自然语言，AI 追问缺失信息并生成结构化组队帖草稿。支持多轮：后端把上一轮草稿（`existing_draft`）和会话历史（`conversation_context`）回传，工作流做增量补全。

## 2. 工作流画布设计（Coze 节点）

```
[开始] → [输入参数校验(代码节点)] → [LLM: 草稿生成与追问] → [输出校验(代码节点)] → [结束]
                                              │
                                              └─ 异常 → [兜底输出(代码节点)] → [结束]
```

| 节点 | 类型 | 说明 |
|------|------|------|
| 开始 | Start | 输入参数：`user_text`(String, 必填)、`user_profile`(Object, 可选)、`existing_draft`(Object, 可选)、`conversation_context`(Array<Object>, 可选) |
| 输入参数校验 | Code | `user_text` 去空白，为空直接报错返回；超长截断到 2000 字 |
| LLM：草稿生成与追问 | LLM | System = system_rules + safety_rules + post_draft_prompt；User = 四个输入变量的 JSON 序列化；开启 JSON 输出模式 |
| 输出校验 | Code | 用 `post_draft.output.json` 校验：必填字段齐全、枚举合法（category/risk_level）；`follow_up_questions` 截断到 3 个；`confidence` 夹到 [0,1] |
| 兜底输出 | Code | LLM 异常或 JSON 解析失败时，输出最小合法结构：`missing_fields=["all"]`、`follow_up_questions=["能再具体说说你想参加什么活动吗？"]`、`risk_level="low"`、`confidence=0`、`draft_text=""`，其余字段 null/空数组 |
| 结束 | End | 输出变量与 `post_draft.output.json` 的 20 个字段一一对应 |

## 3. 多轮交互约定

- 首轮：`existing_draft = null`，`conversation_context = []`。
- 后续轮：后端把上一轮输出的结构化字段作为 `existing_draft` 回传；`conversation_context` 追加用户回答。
- 工作流合并规则：已确认字段不被覆盖，除非用户明确修改；用户跳过的字段保持 `null` + 留在 `missing_fields`。
- 用户选择"跳过追问直接发布"时由前端直接提交当前草稿，缺失字段由后端标注"待确认"（user-flow §3.3）。

## 4. 异常处理

| 异常 | 行为 |
|------|------|
| `user_text` 为空 | 校验节点直接返回错误码，后端提示"请输入需求描述" |
| LLM 超时/失败 | 走兜底输出；后端额外降级为"手动填写表单"入口（test-cases TC-POST-06） |
| 输出 JSON 非法 | 输出校验节点重试一次（带错误信息重新问 LLM），仍失败走兜底 |
| 未配置 `COZE_WORKFLOW_POST_DRAFT` | 后端 `ai_post_draft` 自动切 LLM fallback（见 INTEGRATION.md §4） |

## 5. 测试样例

| 场景 | 输入摘要 | 期望 | 评测集 |
|------|---------|------|--------|
| 美赛一句话 | "我想参加美赛，还缺两个队友，一个会编程一个英语好" | target_members=3、needed_roles=[编程,英文写作]、追问含截止/投入时间 | `evals/post_draft_cases.jsonl` case-01 |
| 信息齐全 | 含活动名+人数+时间+地点 | missing_fields 为空、confidence ≥ 0.8 | case-02 |
| 缺关键信息 | "找人一起自习" | missing_fields 非空、有追问 | case-07 |
| 含联系方式 | 文本中带微信号 | 不写入 description，risk 提示 | case-13 |
| 多轮补全 | existing_draft + "2026年美赛，每周10小时" | time_commitment 更新为 10h/周 | case-19 |
