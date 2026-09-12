# 接口字段对账表

> 版本：v1.0
> 负责人：角色 B（前端）× 角色 C（后端）联合对账
> 日期：2026-08-29
> 状态：B 初稿，待 C 核对
>
> 用途：前端 `packages/shared/src/constants.ts` 定义的 20 个 `/api/*` 接口，
> 逐个对照后端 `src/tools/*.py` 的 tool 参数，标注一致性。
> 后端 `src/api/` 路由层据此实现：从 JWT 提取 user_id，组装 tool 参数。

---

## 约定

1. **`user_id` 注入规则**：凡后端 tool 需要 `user_id` 参数的，**前端不传**，由 `src/api/` 路由层从请求头 `Authorization: Bearer <token>` 解析 JWT 后注入。前端 `client.ts` 已自动携带 token。
2. **统一响应格式**：所有接口返回 `{"code": 0, "message": "ok", "data": <T>}`，前端 `client.ts` 已据此取 `res.data.data`。tool 返回的是 JSON 字符串，`src/api/` 负责解析后包进 `data`。
3. **登录/注册/发验证码**：这三个接口不需要 token（用户还没登录），user_id 由 tool 内部生成或不使用。

---

## 1. 认证模块（6 个）

| # | 接口 | 方法 | 前端传参 | 后端 tool | tool 参数 | user_id | 状态 |
|---|------|------|----------|-----------|-----------|---------|------|
| 1 | `/api/auth/send-code` | POST | `{account}` | `register_auth_send_code` | `account` | 不需要 | ✅一致 |
| 2 | `/api/auth/register` | POST | `{account, code, nickname, major, grade, skills, wechat?}` | `register_user` | `account, code, password, nickname, major, grade, skills, wechat` | 不需要 | ⚠️前端缺 `password` |
| 3 | `/api/auth/login` | POST | `{account, password}` | `login_user` | `account, password` | 不需要 | ✅一致 |
| 4 | `/api/auth/verify-email` | POST | `{email, code}` | `verify_campus_email` | `user_id, email, code` | **JWT 注入** | ⚠️前端缺 user_id，C 从 JWT 注入 |
| 5 | `/api/auth/profile` | GET | 无 | `get_user_profile` | `user_id` | **JWT 注入** | ✅C 从 JWT 注入 |
| 6 | `/api/auth/profile` | PATCH | `{nickname?, major?, grade?, skills?, wechat?}` | `update_user_profile` | `user_id, nickname, major, grade, skills, wechat` | **JWT 注入** | ✅C 从 JWT 注入 |

**⚠️ 接口 2（注册）字段问题**：
- 前端 `types.ts` 的 `RegisterRequest` 没有 `password` 字段，但后端 `register_user` 必填 `password`。
- **处理方案**：B 在 `RegisterRequest` 增加 `password: string`，并在注册页加密码输入框。这是 B 需要改前端的地方。
- 临时方案（演示用）：如果 B 来不及改，C 可在 `src/api/` 里给 password 一个默认值，但不推荐。

---

## 2. 帖子模块（4 个）

| # | 接口 | 方法 | 前端传参 | 后端 tool | tool 参数 | user_id | 状态 |
|---|------|------|----------|-----------|-----------|---------|------|
| 7 | `/api/posts` | GET | `?tab&category&tags&keyword&sort&page&page_size` | `list_posts` | `tab, page, page_size, category, tags, keyword, sort` | 不需要 | ✅一致 |
| 8 | `/api/posts/:id` | GET | 路径参数 id | `get_post_detail` | `post_id` | 不需要 | ✅一致 |
| 9 | `/api/posts` | POST | `{title, activity_name, target_members, needed_roles[], weekly_hours, school_scope, deadline, description, main_category}` | `create_post` | `user_id, title, description, main_category, activity_name, target_members, needed_roles, weekly_hours, school_scope, deadline` | **JWT 注入** | ⚠️前端缺 user_id；needed_roles 前端数组→后端逗号串 |
| 10 | `/api/posts/my` | GET | 无 | `get_my_posts` | `user_id` | **JWT 注入** | ✅C 从 JWT 注入 |

**⚠️ 接口 9（创建帖子）字段问题**：
- `needed_roles`：前端传 `string[]`，后端 tool 收 `str`（逗号分隔）。**C 在 src/api/ 里把数组 `join(",")` 后传给 tool**，B 不用改。
- `main_category`：前端 `createPost(data: Partial<Post>)` 传了，后端 tool 必填。✅一致。
- `user_id`：C 从 JWT 注入。

---

## 3. AI 智能模块（4 个）

| # | 接口 | 方法 | 前端传参 | 后端 tool | tool 参数 | user_id | 状态 |
|---|------|------|----------|-----------|-----------|---------|------|
| 11 | `/api/agent/post-draft` | POST | `{message, draft?, user_skills?}` | `ai_post_draft` | `message, draft, user_skills` | 不需要 | ⚠️类型不一致 |
| 12 | `/api/agent/classify-review` | POST | `Partial<Post>`（含 title, description） | `ai_classify_review` | `post_title, post_description` | 不需要 | ⚠️字段名不一致 |
| 13 | `/api/agent/match` | POST | `{post_id}` | `ai_match_teammates` | `post_id` | 不需要 | ✅一致 |
| 14 | `/api/agent/team-plan` | POST | `{team_id}` | `ai_team_plan` | `team_id` | 不需要 | ✅一致 |

**⚠️ 接口 11（AI 发帖）类型问题**：
- 前端 `draft` 传 `PostDraft` 对象，后端 tool 收 `str`（JSON 字符串）。**C 在 src/api/ 里 `json.dumps(draft)` 后传给 tool**。
- 前端 `user_skills` 传 `string[]`，后端 tool 收 `str`（逗号分隔）。**C 在 src/api/ 里 `",".join(user_skills)`**。
- B 不用改。

**⚠️ 接口 12（分类审核）字段名问题**：
- 前端传 `{title, description}`，后端 tool 收 `post_title, post_description`。**C 在 src/api/ 里做字段映射**。B 不用改。

---

## 4. 申请模块（5 个）

| # | 接口 | 方法 | 前端传参 | 后端 tool | tool 参数 | user_id | 状态 |
|---|------|------|----------|-----------|-----------|---------|------|
| 15 | `/api/applications` | POST | `{post_id, role_wanted, experience, available_time, reason, questions?[]}` | `create_application` | `user_id, post_id, role_wanted, experience, available_time, reason, questions` | **JWT 注入** | ⚠️前端缺 user_id；questions 数组→逗号串 |
| 16 | `/api/applications` | GET | `?post_id` | `get_applications` | `user_id, post_id` | **JWT 注入** | ✅C 从 JWT 注入 |
| 17 | `/api/applications/:id/accept` | POST | 路径参数 id | `accept_application` | `user_id, application_id` | **JWT 注入** | ✅C 从 JWT 注入 |
| 18 | `/api/applications/:id/reject` | POST | 路径参数 id | `reject_application` | `user_id, application_id` | **JWT 注入** | ✅C 从 JWT 注入 |
| 19 | `/api/applications/my` | GET | 无 | `get_my_applications` | `user_id` | **JWT 注入** | ✅C 从 JWT 注入 |

**⚠️ 接口 15（创建申请）字段问题**：
- `questions`：前端传 `string[]`，后端 tool 收 `str`（逗号分隔）。**C 在 src/api/ 里 `",".join(questions)`**。
- `user_id`：C 从 JWT 注入。

---

## 5. 消息模块（5 个）

| # | 接口 | 方法 | 前端传参 | 后端 tool | tool 参数 | user_id | 状态 |
|---|------|------|----------|-----------|-----------|---------|------|
| 20 | `/api/messages/conversations` | GET | 无 | `get_conversations` | `user_id` | **JWT 注入** | ✅C 从 JWT 注入 |
| 21 | `/api/messages/:conversationId` | GET | 路径参数 | `get_messages` | `user_id, conversation_id` | **JWT 注入** | ✅C 从 JWT 注入 |
| 22 | `/api/messages/:conversationId/send` | POST | `{content}` | `send_message` | `user_id, conversation_id, content` | **JWT 注入** | ✅C 从 JWT 注入 |
| 23 | `/api/messages/:conversationId/confirm-team` | POST | 无 | `confirm_team` | `user_id, conversation_id` | **JWT 注入** | ✅C 从 JWT 注入 |
| 24 | `/api/messages/:conversationId/close` | POST | 无 | `close_conversation` | `user_id, conversation_id` | **JWT 注入** | ✅C 从 JWT 注入 |

---

## 6. 团队模块（3 个）

| # | 接口 | 方法 | 前端传参 | 后端 tool | tool 参数 | user_id | 状态 |
|---|------|------|----------|-----------|-----------|---------|------|
| 25 | `/api/teams/:id` | GET | 路径参数 | `get_team_detail` | `user_id, team_id` | **JWT 注入** | ✅C 从 JWT 注入 |
| 26 | `/api/teams/:id/tasks/:taskId` | PATCH | `{done}` | `update_team_task` | `user_id, team_id, task_id, done` | **JWT 注入** | ✅C 从 JWT 注入 |
| 27 | `/api/teams/my` | GET | 无 | `get_my_teams` | `user_id` | **JWT 注入** | ✅C 从 JWT 注入 |

---

## 汇总：B 需要改前端的地方

| 项 | 位置 | 改动 |
|----|------|------|
| 1 | `packages/shared/src/types.ts` `RegisterRequest` | 增加 `password: string` 字段 |
| 2 | `apps/web/src/pages/Login.tsx` 注册表单 | 增加密码输入框，提交时带 `password` |

其余所有不一致都由 **C 在 `src/api/` 里做转换**（user_id 注入、数组↔逗号串、字段名映射、对象↔JSON串），B 不用改。

---

## 汇总：C 在 src/api/ 里要做的转换

| 转换类型 | 涉及接口 | 做法 |
|----------|----------|------|
| JWT → user_id | 4,5,6,9,10,15-27 | `verify_token(token)["user_id"]` |
| `string[]` → `","`.join | 9(needed_roles), 11(user_skills), 15(questions) | `",".join(arr)` |
| 对象 → JSON 字符串 | 11(draft) | `json.dumps(obj)` |
| 字段名映射 | 12(title→post_title, description→post_description) | 手动取值 |
| tool 返回的 JSON 字符串 → dict | 全部 | `json.loads(tool_result)` 后包进 `{code,message,data}` |

---

## 7. 标准标签与候选审核

所有接口都要求登录，候选审核接口仅允许 `site_role=operator` 的运营账号调用。

| 接口 | 方法 | 用途 |
|------|------|------|
| `/api/tags` | GET | 获取当前启用的标准标签与别名 |
| `/api/tags/suggestions?q=` | GET | 用标准名称或已审核别名搜索标签 |
| `/api/tags/proposals` | POST | 提交库外可复用概念，参数为 `name/category/source_text/suggested_tag_id?` |
| `/api/tags/proposals?status=pending` | GET | 运营人员查看候选标签 |
| `/api/tags/proposals/:id/review` | POST | 运营人员执行 `approve/merge/reject` |

`/api/agent/classify-review` 会把帖子标题和描述传给 AI，并提供当前标准标签候选。AI 返回的 `tag_ids` 必须来自候选集合；可选的 `unknown_concepts` 结构如下：

```json
{
  "unknown_concepts": [
    {"name": "定向越野", "category": "activity", "reason": "当前标准库中没有对应活动"}
  ]
}
```

后端只接受 `activity/skill/role/level/audience` 分类、2 至 30 字符的名称，最多处理 5 个候选。合法候选进入 `pending` 队列，不会自动成为标准标签。

---

## 8. 话题与帖子定向授权

授权采用“邀请 -> 用户接受 -> 生效”的流程，支持到期和撤销。平台运营可以管理全部话题与帖子；认证组织负责人可以管理本组织话题；普通发布者只自动管理自己创建的内容。

| 对象 | 角色 | 能力 |
|------|------|------|
| 话题 | `coordinator` | 管理该话题下的组队帖 |
| 话题 | `editor` | 管理组队帖、编辑话题资料 |
| 话题 | `manager` | 管理组队帖、编辑话题资料、管理协作者 |
| 帖子 | `application_manager` | 查看和处理申请、更新招募状态、运行队友匹配 |
| 帖子 | `editor` | 申请管理能力及帖子内容编辑 |

| 接口 | 方法 | 用途 |
|------|------|------|
| `/api/topics/:id/collaborators` | GET / POST | 查看或邀请话题协作者 |
| `/api/topics/:id/collaborators/accept` | POST | 受邀用户接受话题授权 |
| `/api/topics/:id/collaborators/:userId` | DELETE | 撤销话题授权 |
| `/api/posts/:id/collaborators` | GET / POST | 查看或邀请帖子协作者 |
| `/api/posts/:id/collaborators/accept` | POST | 受邀用户接受帖子授权 |
| `/api/posts/:id/collaborators/:userId` | DELETE | 撤销帖子授权 |
| `/api/posts/:id` | PATCH | 按角色能力编辑帖子或更新招募状态 |
| `/api/topics/:topicId/posts/:postId/moderation` | PATCH | 管理话题下的组队帖状态 |

授权邀请、接受、撤销，以及话题/帖子编辑、申请接受或拒绝、话题内帖子管理都会写入审计日志。
