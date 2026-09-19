# 工作流 1：需求拆解与发帖（四字段版）

| 配置 | 值 |
|------|----|
| Coze 名称 | `campusmate_post_draft` |
| 网站接口 | `POST /api/agent/post-draft` |
| Render 变量 | `COZE_POST_DRAFT_API_URL` |
| 输入 Schema | `coze/schemas/post_draft.input.json` |
| 输出 Schema | `coze/schemas/post_draft.output.json` |

## 当前模型

工作流只负责理解并补齐四个核心字段：

- `activity`：准备参与或组织的事情。
- `time`：自然语言时间及规范化结果。
- `location`：地点及规范化结果。
- `people`：总人数、已有成员数和还需招募人数。

`missing_fields`、`next_field` 与 `is_complete` 由工作流统一决定。网站不得再按旧七字段重新计算完成度。旧字段 `needed_roles/weekly_hours/school_scope/deadline` 如仍为发布必填项，在确认页由用户补充。

## 画布

`开始 -> 输入整理/历史草稿合并 -> 对话理解 -> 路由判断`

- `CALL_TOOL`：进入真实网络搜索子图，最多两轮，然后回到理解节点。
- `ASK_USER`：返回一条合并后的自然追问。
- `READY`：进入卡片生成模型，再做输出校验并结束。

循环只能通过子图实现。模型提示词保存在节点配置 JSON 中，一个模型节点只绑定一个模型。

## 状态规则

1. 首轮 `draft` 必须为 `""`。
2. 后续轮次把上一次返回的 `draft` 序列化为 JSON 字符串原样传回。
3. `field_states` 原样回传，只允许四个核心字段。
4. 用户只修改一个字段时，其余已确认字段必须保留。
5. `degraded=true` 的结果不可信；后端保留上一轮草稿并提示重试。
6. `suggested_tag_ids` 只能来自 `candidate_tags`，去重后最多四项。

## 后端兼容

后端保留四字段工作流状态，同时将其投影到现有发布表单：

- `activity.value -> activity_name`
- `people.total_people -> target_members`
- `time.value -> weekly_hours`（页面显示为“时间安排”）
- `location.value -> school_scope`（页面显示为“校区或地点”）
- `description -> description`

投影仅用于当前帖子数据库兼容，不回写工作流状态。

## 验收

逐条运行 `coze/evals/post_draft_cases.jsonl` 的六组用例，覆盖玄武湖地点确认、新街口火锅直接完成、只修改时间、空白降级、正式话题组队和红山动物园志愿活动。
