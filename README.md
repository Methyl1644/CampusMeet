# CampusMate AI

> A trustworthy AI-powered campus team-matching platform that helps university students go from "want to participate" to "actually forming a team."

CampusMate AI 不只是一个带 AI 审核的校园论坛，而是由智能体负责理解需求、合理分类、补全信息、匹配队友、辅助沟通并推动团队真正组建的可信组队平台。

## ✨ 核心功能

- **AI 对话式发帖**：用户输入一句话，AI 追问缺失信息并生成结构化组队帖
- **智能分类与审核**：AI 自动分类、打标签、风险分级，规则引擎 + 语义判断双重审核
- **队友匹配与推荐**：确定性筛选 + 语义匹配，输出可解释的推荐理由
- **申请与临时聊天**：申请加入 → 发布者接受 → 平台内安全聊天
- **双向确认成队**：双方确认后创建团队并解锁联系方式
- **AI 成队规划**：自动生成分工建议、首次会议议程、任务清单和风险提醒
- **分层内容发现**：官方赛事、认证组织活动先进入话题，再查看组队帖；日常搭子直接发布
- **受控标签搜索**：简称和别名映射到标准标签，未知输入不会污染标签库

## 🛠 技术栈

| 层 | 技术 | 说明 |
|----|------|------|
| 前端 | React / Vue（响应式 Web + PWA） | Windows 桌面端与手机端共用 |
| 后端 | Python 3.12 + FastAPI + LangGraph + SQLAlchemy | 用户、帖子、聊天、安全、Coze 调用，`src/` |
| 智能体 | Coze 工作流 | 5 个核心工作流 |
| 数据库 | PostgreSQL / MySQL | 用户、帖子、申请、聊天、团队 |

## 📁 仓库结构

```
campusmate/
├── apps/
│   └── web/              # 前端：React + Vite 响应式界面
├── packages/
│   └── shared/           # 前后端共享类型、接口 schema、常量
├── src/                  # 后端：FastAPI + LangGraph
│   ├── main.py           # FastAPI 入口
│   ├── api/              # /api/* REST 模块化路由（接前端）
│   ├── agents/           # LangGraph agent 定义
│   └── tools/            # 业务工具（认证/帖子/申请/消息/团队/AI/安全）
├── coze/                 # Coze 工作流说明、输入输出样例、Prompt 版本
├── scripts/              # 初始化数据、演示数据、运行脚本
│   └── seed.py           # 灌入演示数据
├── docs/                 # 产品文档、接口文档、测试记录、答辩材料
└── README.md
```

## 👥 团队分工

| 成员 | 角色 | 职责 |
|------|------|------|
| 洪昱童 | A - 产品与设计 | PRD、用户流程、页面定义、原型、演示故事线 |
| 李金泽 | B - 前端开发 | Windows/手机端界面、状态管理、聊天界面 |
| 李雨桐 | C - 后端与安全 | API、数据库、认证、Coze 封装、安全规则 |
| 裴斐 | D - 智能体与算法 | Coze 工作流、Prompt、分类/匹配/审核、评测集 |

## 🚀 快速开始

### 环境要求

- Node.js >= 18 / Python >= 3.10
- Git
- 包管理器：npm / pnpm / uv（按子项目选择）

### 克隆仓库

```bash
git clone <仓库地址>
cd campusmate
git checkout dev
git pull origin dev
```

### 环境变量

复制 `.env.example` 并填写配置：

```bash
cp .env.example .env
```

```env
# 本地可留空并自动使用 campusmate.db；部署时填写 PostgreSQL
DATABASE_URL=

# 本地联调可设 true，生产环境必须为 false
AUTH_TEST_MODE=true

# 仅在 Coze 模型凭据已配置时开启
ENABLE_AGENT_RUNTIME=false

# JWT 密钥
JWT_SECRET=

# Coze 工作流（可选，未配置时后端走 LLM 兜底，不影响演示）
COZE_API_TOKEN=
COZE_WORKFLOW_POST_DRAFT=
COZE_WORKFLOW_CLASSIFY_REVIEW=
COZE_WORKFLOW_MATCH=
COZE_WORKFLOW_OFFICIAL_ACTIVITY_EXTRACT=
COZE_WORKFLOW_TEAM_PLAN=
```

### 启动开发

```bash
# 后端（端口 3000，前端 vite 已把 /api 代理到此）
python src/main.py -m http -p 3000

# 前端
cd apps/web
npm install
npm run dev
```

> 后端首次启动会自动建表。建表后另开终端运行 `python scripts/seed.py` 灌入演示数据。

仅希望为已有本地账号追加新版话题与标签预览数据时，运行：

```bash
python scripts/seed_content_preview.py
```

该脚本幂等执行，不会清空注册用户。

本地未配置短信网关时，手机验证码会以测试模式返回并显示在登录页提示中；这只用于开发联调。生产部署必须设置 `AUTH_TEST_MODE=false` 并接入短信服务，否则手机验证码接口会明确提示改用邮箱或联系管理员。

新版内容接口包括 `/api/topics`、`/api/topics/:id/posts`、`/api/search/suggestions`、`/api/tags/suggestions`、`/api/me/permissions` 和组织认证接口，均要求登录。Coze 交付审计与剩余上线条件见 `docs/coze-result-review-2026-09-10.md`。

## 🔀 Git 协作规范

### 分支结构

```
main        # 稳定演示版本，只接受修复和文档更新
  └── dev   # 日常集成分支
       ├── feat/a-*    # 角色A的工作分支
       ├── feat/b-*    # 角色B的工作分支
       ├── feat/c-*    # 角色C的工作分支
       └── feat/d-*    # 角色D的工作分支
```

### 日常工作流程

```bash
# 1. 每天开始：拉取最新代码
git checkout dev
git pull origin dev

# 2. 创建工作分支
git checkout -b feat/your-task-name

# 3. 完成功能后提交
git add .
git commit -m "feat(server): add application accept API"
git push origin feat/your-task-name

# 4. 发起 PR → 目标分支 dev，至少一人 review
```

### 提交信息格式

```
类型(范围): 简短描述
```

| 类型 | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat(frontend): add post detail page` |
| `fix` | 修复 | `fix(auth): handle expired token` |
| `docs` | 文档 | `docs(prd): update MVP scope` |
| `chore` | 杂项 | `chore(repo): add environment example` |

### 合并规则

1. **不直接向 main 推送**
2. **每个 PR 只做一个清晰任务**
3. **至少一名非作者成员 review**
4. **合并前必须能本地运行**
5. **接口变更时同步更新 `packages/shared` 和 `docs/api.md`**

## 📌 MVP 范围

### 首期支持

- [x] 用户认证与基础资料
- [x] 活动/组队帖浏览
- [x] AI 对话式发帖
- [x] 分类、标签和安全审核
- [x] 队友匹配与推荐理由
- [x] 申请加入与临时聊天
- [x] 双向确认成队与联系方式解锁
- [x] AI 生成分工与第一次会议计划

### 暂缓

- 支付、押金、复杂信用评分
- 全校官网自动抓取
- 语音视频通话
- 跨校组队（首期限南京大学校内）
- iOS/Android 原生 App

## 📄 相关文档

- [产品需求文档](docs/prd.md)
- [用户主流程](docs/user-flow.md)
- [页面定义与验收标准](docs/pages.md)
- [演示故事线](docs/demo-script.md)
- [测试用例](docs/test-cases.md)
- [走查记录](docs/review-notes.md)

## 📜 License

MIT
