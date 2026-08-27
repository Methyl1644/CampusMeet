# 工作流②：分类与审核（classify-review）

| 项 | 内容 |
|----|------|
| 工作流名（Coze 后台） | `campusmate_classify_review` |
| 对应后端工具 | `ai_classify_review`（`src/tools/ai_tools.py`） |
| 对应前端接口 | `POST /api/agent/classify-review` |
| 环境变量 | `COZE_WORKFLOW_CLASSIFY_REVIEW_ID` |
| 输入 Schema | `coze/schemas/classify_review.input.json` |
| 输出 Schema | `coze/schemas/classify_review.output.json` |
| Prompt | `coze/prompts/classify_review_prompt.md`（前置拼接 `system_rules.md` + `safety_rules.md`） |
| 优先级 | P0（对应功能 F06） |

## 1. 目标

帖子提交后自动完成：主分类、动态标签、结构化条件、风险等级、脱敏建议、审核建议。

**层级关系（重要）**：后端 `src/utils/security.py` 规则引擎先做初筛（身份证号/手机号/违禁词/精确住址），通过后调用本工作流做语义级判断。**后端规则是最终拦截层，本工作流不替代它**（PRD §5.4）。

## 2. 工作流画布设计（Coze 节点）

```
[开始] → [输入校验+脱敏复查(代码节点)] → [LLM: 分类与审核] → [输出校验(代码节点)] → [结束]
                                                     │
                                                     └─ 异常 → [保守兜底: 转人工] → [结束]
```

| 节点 | 类型 | 说明 |
|------|------|------|
| 开始 | Start | 输入：`post_draft`(Object)、`user_auth_level`(String)、`source_type`(String)、`raw_text`(String) |
| 输入校验+脱敏复查 | Code | 复查 `raw_text` 是否仍含手机号/微信号/身份证号正则命中；命中则先掩码并在输出 `reviewer_note` 追加"输入疑似含未脱敏敏感信息" |
| LLM：分类与审核 | LLM | System = system_rules + safety_rules + classify_review_prompt；JSON 输出模式 |
| 输出校验 | Code | 校验枚举：`main_category` 必须命中 6 个主分类之一；`audit_result` ∈ {approve, modify, manual_review, reject}；`risk_level=high` 时强制 `needs_manual_review=true`；`audit_result=modify` 时 `suggested_revision` 必填 |
| 保守兜底 | Code | LLM 失败时输出 `audit_result="manual_review"`、`needs_manual_review=true`、`reviewer_note="AI 审核服务异常，转人工"`，其余按输入原样回填 |
| 结束 | End | 输出 12 个字段 |

## 3. 审核判定矩阵（Prompt 规则的汇总）

| 场景 | risk_level | audit_result | needs_manual_review |
|------|-----------|--------------|---------------------|
| 学业场景，无风险点（比赛/科研/课程/学习搭子） | low | approve | false |
| 含可脱敏的联系方式 | low~medium | modify | false |
| 线下/夜间/AA 金钱/长途 | medium | approve 或 modify | false |
| 疑似违规但不确定 | high | manual_review | true |
| 明确违规（代写/诈骗/倒卖/押金借贷） | high | reject | true |

## 4. 异常处理

| 异常 | 行为 |
|------|------|
| LLM 超时/失败 | 保守兜底转人工，帖子进入待审核队列（user-flow §4.1） |
| 输出枚举非法 | 输出校验节点修正为最近合法值并记日志，无法修正则转人工 |
| 输入含未脱敏敏感信息 | 掩码后继续，reviewer_note 记录（不阻塞，因后端规则层仍兜底） |
| 未配置工作流 ID | 后端切 LLM fallback，fallback 失败则帖子进待审核队列 |

## 5. 测试样例

| 场景 | 输入摘要 | 期望 | 评测集 |
|------|---------|------|--------|
| 正常美赛帖 | 小王美赛招募 | 竞赛与项目 / low / approve | `evals/classify_review_cases.jsonl` case-01 |
| 含手机号 | 正文带 138 开头号码 | blocked_fields 含手机号、modify、sanitized_text 已掩码 | case-08 |
| 代写 | "代写数据结构作业 200 元" | high / reject | case-11 |
| 押金 | "入队先交 100 押金" | high / manual_review 或 reject | case-12 |
| 夜间篮球 | "晚上 11 点约球" | medium / 风险提示 | case-06 |
| 正常内容防误杀 | 口语化课程作业帖 | 不误判违规 | case-04 |
