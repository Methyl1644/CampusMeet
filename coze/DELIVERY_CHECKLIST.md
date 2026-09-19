# CampusMate Coze 前两项交付清单

这份清单对应当前网站后端契约。先创建并发布两个工作流，再把部署 API 地址配到 Render；不要在 Coze 中自行改字段名。

## 一、创建 `campusmate_post_draft`

1. 在 Coze 新建工作流，名称填 `campusmate_post_draft`。
2. 按 `workflows/01_post_draft.md` 核对四字段状态、搜索子图、路由判断、卡片生成和降级分支。
3. 开始和结束变量分别照 `schemas/post_draft.input.json`、`schemas/post_draft.output.json` 建立。
4. 使用当前已部署节点配置中的提示词；不要再粘贴旧七字段 `post_draft_prompt.md` 覆盖新配置。
5. `next_field` 在 Coze 结束节点设为可选 String；没有下一字段时输出空字符串，后端会转换为 `null`。
6. 用 `evals/post_draft_cases.jsonl` 逐条试运行；全部通过后发布并复制 `/run` API 地址。

## 二、创建 `campusmate_classify_review`

1. 新建工作流，名称填 `campusmate_classify_review`。
2. 按 `workflows/02_classify_review.md` 创建开始、输入校验、大模型、白名单校验、保守兜底、结束节点。
3. 开始和结束变量分别照 `schemas/classify_review.input.json`、`schemas/classify_review.output.json` 建立。
4. 大模型节点提示词依次粘贴 `prompts/system_rules.md`、`prompts/safety_rules.md`、`prompts/classify_review_prompt.md`。
5. 用 `evals/classify_review_cases.jsonl` 逐条试运行；全部通过后发布并复制 `/run` API 地址。

## 三、Render 配置

在 `campusmate-api` 的 Environment 中添加或更新：

```text
COZE_DEPLOY_API_TOKEN=<部署页生成的 API Token>
COZE_POST_DRAFT_API_URL=<第一个工作流的 https://...coze.site/run 地址>
COZE_CLASSIFY_REVIEW_API_URL=<第二个工作流的 https://...coze.site/run 地址>
```

只完成第一个工作流时，第二个 URL 可以暂时留空。保存后等待 Render 自动重新部署。Token 只放 Render，不发到聊天、不写入仓库，也不放前端静态站点。旧版 `COZE_API_TOKEN + COZE_WORKFLOW_*` 仍受支持，但只作为后备方式。

## 四、网站验收

1. 登录已完成校园邮箱验证的账号。
2. 在发帖页输入一句不完整需求，确认 AI 只追问四字段中的关键缺失信息，并保留前面答案。
3. 完整填写后确认推荐标签都来自标准标签库。
4. 提交普通内容，确认返回低风险；再用测试用例中的高风险文案，确认给出风险提示。
5. 在 Render 日志中确认 Coze 请求成功；临时把某个 API URL 填错，确认网站仍能降级工作而不是阻断发帖。
