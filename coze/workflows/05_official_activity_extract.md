# 工作流⑤（P1 可选）：官方活动信息抽取（official-activity-extract）

| 项 | 内容 |
|----|------|
| 工作流名（Coze 后台） | `campusmate_official_activity_extract` |
| 对应后端能力 | 官方活动录入辅助（F14）；首期官方活动以人工录入为主，本工作流仅做格式化辅助，**不阻塞 P0** |
| 环境变量 | `COZE_WORKFLOW_OFFICIAL_ACTIVITY_EXTRACT_ID`（可选） |
| 优先级 | P1 |

## 1. 目标

把官方页面（学校官网、学院官网、赛事主办方页面）的活动文本转成标准活动卡，供运营人工确认后录入。首期不做全网自动抓取（PRD §2.2），输入文本由运营粘贴。

## 2. 输入 / 输出（简版约定）

**输入**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `page_text` | String | 运营粘贴的官方页面正文（已去除导航等噪声） |
| `source_url` | String | 来源链接（须为白名单域名） |
| `source_org` | String | 来源机构，如"南京大学教务处" |

**输出**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `activity_name` | String | 活动名 |
| `organizer` | String | 主办方 |
| `category` | String | 6 个主分类之一 |
| `signup_deadline` | String/null | 报名截止 YYYY-MM-DD |
| `activity_time` | String/null | 活动时间 |
| `team_size` | String/null | 队伍规模，如"3人一队" |
| `requirements_summary` | String | 参赛要求摘要（≤200字） |
| `tags` | Array<String> | 动态标签 |
| `confidence` | Number | 抽取置信度；低于 0.6 时提示运营人工核对 |
| `missing_fields` | Array<String> | 页面上找不到的字段 |

## 3. 约束

1. **只抽取不改写**：日期、人数、要求必须来自原文，原文没有的一律 `null` 并进 `missing_fields`，不得根据"常识"补（如不得默认美赛截止是某天）。
2. **来源白名单**：`source_url` 域名须在学校/主办方白名单内，否则输出标记 `confidence ≤ 0.5` 并提示人工核实。
3. 输出一律进入**人工确认队列**，不直接上架展示（信息层级：官方来源也须经运营确认录入，见 PRD §5.1）。

## 4. 画布节点（简版）

```
[开始] → [白名单域名校验(代码)] → [LLM: 字段抽取] → [输出校验(代码)] → [结束]
```

## 5. 与其他工作流的关系

- 抽取结果确认入库后，可作为 `post-draft` 的 `activity_name` 联想来源、以及 `match-teammates` 中 `deadline` 的校准依据。
- P0 阶段若本工作流未上线，官方活动由人工按同一字段结构录入，不影响主闭环。
