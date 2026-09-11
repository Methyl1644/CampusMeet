# CampusMate Coze 前两项交付清单

这份清单对应当前网站后端契约。先创建并发布两个工作流，再把 ID 配到 Render；不要在 Coze 中自行改字段名。

## 一、创建 `campusmate_post_draft`

1. 在 Coze 新建工作流，名称填 `campusmate_post_draft`。
2. 按 `workflows/01_post_draft.md` 创建开始、输入整理、大模型、输出校验、安全兜底、结束节点。
3. 开始和结束变量分别照 `schemas/post_draft.input.json`、`schemas/post_draft.output.json` 建立。
4. 大模型节点提示词依次粘贴 `prompts/system_rules.md`、`prompts/safety_rules.md`、`prompts/post_draft_prompt.md`。
5. 用 `evals/post_draft_cases.jsonl` 逐条试运行；全部通过后发布并复制工作流 ID。

## 二、创建 `campusmate_classify_review`

1. 新建工作流，名称填 `campusmate_classify_review`。
2. 按 `workflows/02_classify_review.md` 创建开始、输入校验、大模型、白名单校验、保守兜底、结束节点。
3. 开始和结束变量分别照 `schemas/classify_review.input.json`、`schemas/classify_review.output.json` 建立。
4. 大模型节点提示词依次粘贴 `prompts/system_rules.md`、`prompts/safety_rules.md`、`prompts/classify_review_prompt.md`。
5. 用 `evals/classify_review_cases.jsonl` 逐条试运行；全部通过后发布并复制工作流 ID。

## 三、Render 配置

在 `campusmate-api` 的 Environment 中添加或更新：

```text
COZE_API_TOKEN=<Coze 个人访问令牌>
COZE_API_BASE_URL=https://api.coze.cn
COZE_WORKFLOW_POST_DRAFT=<第一个工作流 ID>
COZE_WORKFLOW_CLASSIFY_REVIEW=<第二个工作流 ID>
```

保存后等待 Render 自动重新部署。Token 只放 Render，不发到聊天、不写入仓库，也不放前端静态站点。

## 四、网站验收

1. 登录已完成校园邮箱验证的账号。
2. 在发帖页输入一句不完整需求，确认 AI 能逐项追问并保留前面答案。
3. 完整填写后确认推荐标签都来自标准标签库。
4. 提交普通内容，确认返回低风险；再用测试用例中的高风险文案，确认给出风险提示。
5. 在 Render 日志中确认 Coze 请求成功；临时把某个工作流 ID 填错，确认网站仍能降级工作而不是阻断发帖。
