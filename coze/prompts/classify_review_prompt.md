# 工作流② Prompt：分类与审核（classify_review）

> 前置：先拼接 `system_rules.md` + `safety_rules.md`，再接本 Prompt。
> 输出 Schema：`coze/schemas/classify_review.output.json`
> 定位：AI 语义判断层。规则引擎初筛在前，本工作流补充语义级判断；最终处置由后端规则决定。

---

## 任务

对已提交的帖子做四件事：**分类打标、结构化条件抽取、风险评估、审核建议与修改建议**。

## 输入变量

- `{{post_draft}}`：结构化草稿
- `{{user_auth_level}}`：发帖者认证等级
- `{{source_type}}`：来源类型
- `{{raw_text}}`：脱敏后的帖子全文

## 处理步骤

1. **主分类**：从 6 个主分类中选 1 个：
   - 竞赛与项目（比赛、创新创业、编程项目）
   - 学习与科研（科研、课程作业、学习搭子、自习打卡）
   - 体育与健身（球类、跑步、健身房搭子）
   - 旅行与户外（旅行、登山、露营）
   - 校园生活（二手、失物、社团招新、日常互助）
   - 拼团与AA（拼单、AA 聚餐、拼车）
2. **动态标签**：3-8 个，覆盖：活动领域（数学建模、Python）、地点（仙林校区）、时间（周末、暑假）、人群适配（新手友好）、形式（线上、线下）。
3. **结构化条件**：抽取时间、地点、人数、所需能力、截止日期，填 `structured_conditions`。
4. **风险评估**（按 safety_rules 第 1-4 节）：
   - 命中敏感信息/违规内容 → high 或按规则处理；
   - 线下/夜间/金钱/长途 → medium；
   - 学业场景无风险点 → low。
   `risk_reasons` 逐条写清原因，引用具体文本依据。
5. **审核建议**：
   - `approve`：直接通过（low）
   - `modify`：脱敏/删改后可通过（含可移除的联系方式、表述不当）
   - `manual_review`：拿不准或 high 但非明确违规
   - `reject`：明确违规（代写、诈骗、倒卖）
   high 风险时 `needs_manual_review = true`。
6. **脱敏与修改建议**：输出 `sanitized_text`（掩码后全文）；需修改时 `suggested_revision` 用可执行的话术（"删除第 2 句中的微信号"）；转人工时 `reviewer_note` 写明疑点。
7. **不误杀**：正常组队内容（哪怕写得口语化）不得误判；只标记有明确依据的风险。

## 信任加成参考

- `source_type = official`：内容一般可信，重点查敏感信息。
- `source_type = org`：正常审核。
- `user_auth_level = unverified`：涉及金钱/线下场景时风险升一级。

## 示例

输入：小王的美赛招募帖（编程+英文写作，10h/周，南京大学优先）。

输出要点：
- `main_category`: "竞赛与项目"
- `dynamic_tags`: ["数学建模", "美赛", "Python", "英文写作", "新手友好"]
- `risk_level`: "low", `audit_result`: "approve", `needs_manual_review`: false
- `suggested_revision`: null
