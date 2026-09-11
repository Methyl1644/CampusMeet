# CampusMate 新版前端草图与联调交接

更新日期：2026-09-09

## 1. 给团队的简短说明

目前已经完成新版 CampusMate 的可点击前端草图，重点确定了内容架构、话题与组队帖的层级、统一搜索、标准标签、AI 辅助发帖、认证和角色权限的交互方式。

这两份 HTML 是产品与交互基准，不是可以直接替换 `apps/web` 的正式实现。草图中的账号、话题、标签、帖子、消息和 AI 结果均为本地示例。下一步需要 B 将界面迁移为 React，C 补齐数据库、权限和 API，D 完成标准标签及 AI 契约，A 确认内容与运营规则。

预览文件：

- `docs/prototypes/CampusMate-auth-prototype.html`
- `docs/prototypes/CampusMate-interactive-prototype.html`

建议先打开认证草图，登录或完成注册演示后进入内容草图。

## 2. 已确定的产品规则

### 2.1 三类内容

| 频道 | 内容 | 发布者 | 页面关系 |
| --- | --- | --- | --- |
| 官方赛事与项目 | 正规比赛、项目及权威信息 | 平台运营账号 | 先进入话题，再查看资料和组队帖 |
| 认证组织活动 | 学院、书院、社团和认证组织活动 | 该组织授权发布者 | 先进入话题，再查看资料和组队帖 |
| 同学自主组队 | 体育、约饭、拍照、出游、学习和项目搭子 | 校园认证用户 | 直接进入具体邀约，不强制建立话题 |

### 2.2 话题

- 话题是官方或认证组织发布的高优先级内容，不等于普通组队帖。
- 同一赛事的同一届次和主办方只保留一个话题，更新信息应修改已有话题。
- 正规赛事组队帖必须关联 `topic_id`。
- 话题详情包括活动介绍、资料与来源、关注人数和组队招募区。
- 用户输入简称或部分关键词时，搜索建议优先显示完整话题名称；点击后直接进入话题详情。

### 2.3 登录与认证

- 未登录用户不能进入站内页面，也不能通过直接调用列表或详情 API 匿名浏览。
- 登录成功后直接进入内容发现页。
- 注册流程为“创建账号 -> 完善资料 -> 校园认证”，只在页面底部显示横向进度。
- 校园认证用户可以发布个人组队帖、申请队伍；组织话题发布还需要组织范围内的发布者角色。
- 组织资质、组织成员和发布者角色必须分别审核和授权，并具有有效期及审计记录。

### 2.4 标签

- 用户和 AI 都不能直接创建标签。
- 标准标签存储为稳定 `tag_id`；显示名称可以修改，但业务关联不能依赖自由文本。
- 非标准名称通过别名映射，例如“羽球 -> 羽毛球”“数模 -> 数学建模”。
- 未命中的词只记录为运营分析数据，经过人工审核后才能新增标准标签或别名。
- 赛事级别、组织、时间、地点、人数和状态优先使用结构化字段，避免全部混为普通标签。

## 3. 当前已有与真实缺口

| 能力 | 当前仓库 | 新设计还需要 |
| --- | --- | --- |
| React 前端 | 已有登录、首页、发现、发布、详情、消息和团队页面 | 按草图重构频道、话题和认证流程 |
| 登录保护 | `MainLayout` 会把未登录用户跳到 `/login` | 后端列表、详情和搜索接口也必须验证 Token |
| 帖子 | 已有 `posts` 表和创建、列表、详情接口 | 增加帖子类型和可空 `topic_id` |
| 话题 | 草图内有示例数据 | 新建模型、接口、来源、届次、关注和去重约束 |
| 标签 | `posts.tags` 是自由 JSON 数组 | 新建标准标签、别名和关联表 |
| AI 草稿 | 已有 `/api/agent/post-draft` | 增加字段状态、候选标签 ID 和严格输出校验 |
| AI 分类 | 已有 `/api/agent/classify-review` | 接入真实发布链路，并限制为标准标签 ID |
| 组织权限 | 草图演示了状态 | 新建组织、申请、成员、邀请、角色和审计模型 |
| 搜索 | 草图使用本地标题和别名匹配 | 后端搜索话题、邀约、标准标签和别名 |

## 4. 建议数据模型

### 4.1 新增表

```text
topics
  id, title, short_title, channel, organizer_id, edition
  summary, content, source_url, source_status
  registration_deadline, activity_start_at, activity_end_at
  follower_count, status, created_by, created_at, updated_at

organizations
  id, name, type, school_scope, verification_status
  verified_at, expires_at

organization_members
  organization_id, user_id, role
  status, invited_by, effective_at, expires_at

tags
  id, code, canonical_name, category, status, display_color

tag_aliases
  id, tag_id, normalized_alias, source, status

topic_tags
  topic_id, tag_id, source, confidence

post_tags
  post_id, tag_id, source, confidence
```

### 4.2 修改现有帖子

```text
posts.kind = topic_team | casual_invitation
posts.topic_id = nullable foreign key -> topics.id
```

约束：

- `kind=topic_team` 时 `topic_id` 必填。
- `kind=casual_invitation` 时 `topic_id` 必须为空。
- 话题建议使用 `(organizer_id, canonical_event_key, edition)` 唯一约束。
- 正式关联只保存 `tag_id`，不把 AI 返回的自由文本直接写入数据库。

## 5. 最小 API 契约

| 方法与路径 | 用途 | 权限 |
| --- | --- | --- |
| `GET /api/search/suggestions?q=&channel=` | 话题、邀约和标准标签建议 | 已登录 |
| `GET /api/topics?channel=&tag_ids=&page=` | 话题列表 | 已登录 |
| `GET /api/topics/:id` | 话题资料、来源和关注数 | 已登录 |
| `GET /api/topics/:id/posts` | 话题下的组队帖 | 已登录 |
| `POST /api/topics` | 创建正式话题 | 运营或组织发布者 |
| `PATCH /api/topics/:id` | 更新正式话题 | 原发布组织或运营 |
| `POST /api/topics/:id/follow` | 关注话题 | 已登录 |
| `GET /api/tags/suggestions?q=` | 返回标准标签和别名命中 | 已登录 |
| `POST /api/posts` | 创建组队帖或日常邀约 | 校园认证用户 |
| `POST /api/agent/post-draft` | 多轮补全组队需求 | 校园认证用户 |
| `POST /api/agent/classify-review` | 标准标签建议与风险审核 | 由后端发布流程调用 |
| `GET /api/me/permissions` | 当前账号的校园、组织和发布权限 | 已登录 |

搜索建议的最小响应：

```json
{
  "direct": [
    {
      "entity_type": "topic",
      "entity_id": "topic_123",
      "title": "大学生数学建模竞赛 · 2026",
      "subtitle": "赛事组委会",
      "matched_by": "alias"
    }
  ],
  "tags": [
    {
      "tag_id": "activity_math_modeling",
      "canonical_name": "数学建模",
      "matched_alias": "数模"
    }
  ]
}
```

## 6. AI 与标签的正式运行链路

```text
用户自然语言
-> 后端规则检查与脱敏
-> AI 提取字段、标记缺失项并追问
-> 后端从标准标签库检索少量候选项
-> AI 只能返回候选 tag_id
-> JSON Schema 与权限校验
-> 用户确认字段和标签
-> 后端分类审核
-> 创建帖子及 post_tags 关联
```

字段状态建议统一为：

```text
confirmed | none | unknown | skipped | pending
```

AI 必须接受“无要求、不需要、不知道、待商定、跳过”等答案，不得反复追问已结束的字段。未知标签不得自动插入 `tags` 或 `tag_aliases`。

模型调用顺序建议：Coze 工作流 -> 后端 LLM 适配器 -> 规则匹配和手动表单。Coze Token、模型密钥和工作流 ID 只保存在后端 `.env`，不得出现在浏览器代码或 Git 中。

## 7. 成员任务分配

### A：产品与运营规则

- 确认三频道名称、话题与组队帖边界、话题唯一性规则。
- 给出首批 20-30 个正式话题及可靠来源。
- 确定组织认证材料、审核状态、有效期和复核规则。
- 验收内容文案、信息优先级和关键用户流程。

### B：前端

- 保留现有 React/Vite 架构，把单文件草图拆成页面和可复用组件。
- 新增 `/topics/:id`，在话题详情中显示资料、关注和组队帖。
- 重构发现页为三频道和单一搜索框，接入后端搜索建议。
- 搜索建议先显示“话题直达”，再显示标准标签；支持选中标签和删除标签。
- 把注册流程改为底部横向进度，登录成功直接进入站内。
- 接入权限状态、加载、空状态、接口失败和 AI 降级状态。
- 不把草图中的硬编码账号、标签、帖子和 AI 结果带入正式代码。

### C：后端与安全

- 建立 topics、tags、tag_aliases、组织权限和关联表迁移。
- 实现第 5 节接口，并同步 `packages/shared` 类型。
- 为列表、详情、搜索和 AI 接口统一增加登录校验。
- 在服务端实施话题发布权限、组织范围、有效期和话题去重。
- 发布帖子时依次执行规则审核、AI 分类、标签白名单校验和数据库事务。
- 实现搜索归一化、前缀/包含/别名匹配；必要时增加拼音和模糊匹配。
- 保存权限变更、人工审核和话题更新审计日志。

### D：智能体与算法

- 建立首版标准标签分类、稳定 code、别名和种子数据。
- 修改 post-draft Schema，加入字段状态、缺失字段和候选标签。
- 修改 classify-review Schema，只允许返回后端提供的候选 `tag_id`。
- 补充“简称、错别字、近义词、跳过、暂无要求、AI 超时”评测用例。
- 保持 Coze 与 fallback 的应用层响应一致，并验证异常时可以切换手动表单。
- AI 不直接授予权限、不创建标签、不决定最终发布和封禁。

## 8. 推荐协作顺序

1. A/B/C/D 一起冻结 Topic、Post、Tag、Organization 和权限类型。
2. C 建表并提供 OpenAPI 或模拟响应；D 同时制作标签种子与 AI Schema。
3. B 可先使用冻结的模拟响应迁移草图，不必等待后端全部完成。
4. C 完成接口后，B 逐页替换模拟数据；D 接入 post-draft 和 classify-review。
5. 联调“登录 -> 搜索话题 -> 进入话题 -> 发布组队帖 -> AI 补全与标签确认 -> 发布”主链路。
6. 最后联调组织话题发布、关注、申请、聊天和双向确认成队。

任何接口字段调整都必须同步修改：

- `packages/shared/src/types.ts`
- `packages/shared/src/constants.ts`
- 对应前端 API 文件
- 对应 FastAPI 路由
- `coze/schemas/` 与 `docs/d-ai-contract.md`

## 9. 联调验收清单

- [ ] 未登录访问页面和内容 API 均返回登录要求或 401。
- [ ] 输入“数模”能返回完整数学建模话题并可直接进入。
- [ ] 输入“羽球”只映射为“羽毛球”，数据库不会新增“羽球”标签。
- [ ] 前两个频道的组队帖必须从话题详情进入并关联 `topic_id`。
- [ ] 日常搭子可以独立发布，不生成虚假话题。
- [ ] 普通用户不能发布官方或组织话题。
- [ ] 组织发布者只能管理所属组织的话题，过期角色不能继续发布。
- [ ] AI 接受“无、不知道、跳过”，不会无限追问。
- [ ] AI 输出非法标签、非法枚举或非法 JSON 时被后端拦截。
- [ ] AI 服务失败时仍可手动完成并发布结构化帖子。
- [ ] 手机和桌面端均无横向溢出，搜索建议和按钮文字完整。
- [ ] Token、验证码、密码、证明材料和未脱敏联系方式不会发送给 AI。

## 10. 当前草图验证结果

- 31 项本地状态、权限、发布和搜索测试通过。
- “数模”可优先显示完整话题名称并进入话题详情。
- 三频道均已改为单一搜索入口。
- 登录页已删除访客浏览入口；注册流程使用底部横向进度和阶段动画。
- 当前仍为本地模拟，不代表数据库、邮件、组织审核、模型和生产部署已经完成。
