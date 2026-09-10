# CampusMate 上线操作

这套配置会在 Render 创建两个服务：

- `campusmate-api`：FastAPI 后端，连接 Neon 数据库。
- `campusmate-web`：React 前端，向公开后端发送请求。

所有密码和密钥都只填写在服务控制台中，不要写进代码、截图或聊天消息。

## 1. 准备 Neon 数据库地址

1. 打开 Neon 项目，点击右上角 **Connect**。
2. Branch 选择 `production`，数据库选择 `neondb`，角色选择项目默认 owner。
3. 打开 **Pooled connection**，复制以 `postgresql://` 开头的完整连接地址。
4. 该地址只在 Render 中作为 `DATABASE_URL` 使用。主机名通常带有 `-pooler`。

## 2. 从仓库创建 Render Blueprint

1. 先把本分支推送到 GitHub。
2. 进入 Render Dashboard，选择 **New > Blueprint**。
3. 连接 CampusMate 的 GitHub 仓库，Blueprint Path 保持 `render.yaml`。
4. 选择要部署的分支并开始创建。
5. Render 要求填写变量时，使用下表。初次创建若服务名未被占用，可先使用表中的预计网址；创建完成后要以 Render 页面显示的网址为准复核。

| 服务 | 变量 | 填写内容 |
| --- | --- | --- |
| `campusmate-api` | `DATABASE_URL` | Neon 的 pooled connection 完整地址 |
| `campusmate-api` | `FRONTEND_ORIGINS` | `https://campusmate-web.onrender.com` |
| `campusmate-api` | `BOOTSTRAP_OPERATOR_EMAIL` | 你准备用作平台运营账号的注册邮箱 |
| `campusmate-api` | `RESEND_API_KEY` | Resend 创建的 API Key |
| `campusmate-api` | `RESEND_FROM_EMAIL` | `CampusMate <verify@你的已验证域名>` |
| `campusmate-web` | `VITE_API_BASE_URL` | `https://campusmate-api.onrender.com` |

`JWT_SECRET` 会由 Render 自动生成，不需要自己填写。

`ENABLE_AGENT_RUNTIME=false` 时，旧的 Agent 调试入口全部关闭；网页使用的是受登录保护的 `/api/agent/*` 接口。

## 3. 复核两个公开网址

服务创建后，分别打开它们的 Render 页面并复制页面顶部的实际 URL。

1. 在后端的 **Environment** 中，把 `FRONTEND_ORIGINS` 改为前端实际 URL，不要保留末尾 `/`。
2. 在前端的 **Environment** 中，把 `VITE_API_BASE_URL` 改为后端实际 URL，不要添加 `/api`。
3. 分别点击 **Save, rebuild, and deploy**。Vite 的 API 地址在构建时写入，因此前端变量变化后必须重新部署。
4. 打开 `后端实际URL/health`，应看到 `status` 为 `ok`。

## 4. 开通注册验证码邮件

1. 创建 Resend 账号并添加自己拥有的域名。
2. 按 Resend 页面提供的值，在域名 DNS 中添加 SPF 和 DKIM 记录并等待验证。
3. 创建只用于发送邮件的 API Key，直接填入 Render 的 `RESEND_API_KEY`。
4. 将 `RESEND_FROM_EMAIL` 设为已验证域名下的发件地址，例如 `CampusMate <verify@mail.example.com>`。
5. 使用真实邮箱完成一次注册测试。未验证自有域名时，Resend 默认测试域名只能发送到 Resend 账号本人的邮箱。

当前生产环境支持邮箱验证码注册。手机短信需要另外接入短信供应商，未配置时页面应提示改用邮箱。

## 5. 接入 AI

基础账号、话题、标签和组队帖子不依赖 Coze 即可运行。需要真实 AI 能力时，在 `campusmate-api` 的 **Environment** 中追加：

- `COZE_API_TOKEN`
- `COZE_API_BASE_URL`
- `COZE_WORKFLOW_POST_DRAFT`
- `COZE_WORKFLOW_CLASSIFY_REVIEW`
- `COZE_WORKFLOW_MATCH`
- `COZE_WORKFLOW_TEAM_PLAN`

凭据未配置时，后端继续使用现有规则降级逻辑。不要把任何 Coze 密钥添加到前端变量中。

## 6. 上线验收

1. 后端 `/health` 返回成功。
2. 前端能打开登录页，刷新内部路由不会出现 404。
3. 使用邮箱接收验证码并完成注册、登录和退出。
4. 使用 `BOOTSTRAP_OPERATOR_EMAIL` 对应邮箱注册后，重启一次后端服务，并在个人资料接口确认 `site_role` 为 `operator`。
5. 创建一条组队帖，刷新页面后数据仍存在。
6. 搜索标准标签和官方话题。
7. 配置 Coze 后测试 AI 草稿与标签建议；关闭 Coze 配置后确认规则降级仍可用。
