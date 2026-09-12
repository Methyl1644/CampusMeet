# 工作流 2：标签推荐与风险初筛

| 配置 | 值 |
|------|----|
| Coze 名称 | `campusmate_classify_review` |
| 网站接口 | `POST /api/agent/classify-review` |
| Render 变量 | `COZE_CLASSIFY_REVIEW_API_URL` |
| 输入 Schema | `coze/schemas/classify_review.input.json` |
| 输出 Schema | `coze/schemas/classify_review.output.json` |
| Prompt | `system_rules.md` + `safety_rules.md` + `classify_review_prompt.md` |

## 画布

`开始 -> 输入校验（代码） -> 标签与风险分析（大模型） -> 白名单校验（代码） -> 结束`

异常分支：模型调用或 JSON 解析失败时，进入“保守兜底（代码）”，再连接结束节点。

## 节点配置

1. **开始**：仅创建 `title/description/candidate_tags` 三个变量，全部必填。
2. **输入校验**：标题限制 120 字，正文限制 5000 字，候选标签限制 120 个；移除缺少 `tag_id/canonical_name/category` 的候选。
3. **标签与风险分析**：开启 JSON 输出；系统提示词按表中顺序拼接；将三个输入变量作为 JSON 传入。
4. **白名单校验**：`tag_ids` 只保留候选列表中的 ID，去重并截断为 8 个；候选新概念按名称长度、分类枚举和数量过滤。
5. **保守兜底**：返回 `main_category="校园生活"`、`tag_ids=[]`、`unknown_concepts=[]`、`risk_level="medium"`，并在 `suggestions` 提示稍后重试；后端仍可按规则处理帖子。
6. **结束**：输出 Schema 中五个字段逐一映射。

## 候选新标签规则

- AI 只能提出候选，不能直接加入标准库。
- 后端会再次清洗并存入 `tag_proposals` 的 `pending` 队列。
- 平台运营在 `/api/tags/proposals/:id/review` 执行批准、合并或拒绝。
- “美赛”“挑战杯”等赛事全名归话题库，不作为普通 Tag；同义词优先合并到已有 Tag。

## 验收

使用 `coze/evals/classify_review_cases.jsonl` 至少试运行五例。必须覆盖标准标签命中、库外可复用活动、具体赛事名不建 Tag、联系方式脱敏文本和高风险内容。
