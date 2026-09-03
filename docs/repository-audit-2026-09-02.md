# CampusMate 仓库上传与集成审计

> 审计日期：2026-09-02
> 远程仓库：`Methyl1644/EL_CampusMate`
> 审计基线：`origin/main` 的 `3aa2afc`

## 1. 结论

| 成员 | 上传情况 | 可验证交付 | 结论 |
|------|----------|------------|------|
| A 产品与验收 | 已上传 | `docs/prd.md`、`user-flow.md`、`pages.md`、`demo-script.md`、`test-cases.md`、`e2e-checklist.md`、`api-alignment.md` | 已到位 |
| B 前端 | 已上传到 `main` | `apps/web`、`packages/shared`；React + Vite + TypeScript 生产构建成功 | 已到位 |
| C 后端与安全 | 已上传到 `main` | `src/api/`、`src/tools/`、数据库模型、安全引擎、`scripts/seed.py`；原有 10 项后端测试通过 | 已到位 |
| D 智能体与算法 | 旧资产已上传，本轮收尾在 `feat/d-final-integration` | 四工具契约、规范 Coze 配置、匹配 Schema、fallback 自动化测试、交接文档 | 本地完成，待 PR |

## 2. 分支风险

- `origin/main` 最新为 `3aa2afc`，包含 B/C 集成代码。
- `origin/dev` 仍停在 `ee9cd48`，缺少后续 B/C 提交。
- 团队现阶段不应从旧 `dev` 直接开新功能，否则会看不到 B/C 代码。
- 建议由仓库管理者在 D 的 PR 合并后，用团队认可的方式将 `dev` 同步到 `main`；同步前不要强制覆盖任何人的工作。

## 3. 本轮验证证据

```text
Python: 18 passed
Frontend: TypeScript check + Vite production build passed
Coze assets: 9 JSON files + 85 JSONL records parsed successfully
Git diff: no whitespace errors
```

## 4. 剩余外部条件

1. 真实 Coze workflow ID 仍为可选；留空即走 fallback。
2. 开启 `COZE_WORKFLOW_MATCH` 前，必须先在 Coze 工作流中完成受控、已脱敏的上下文查询节点。
3. 完整端到端演示仍需本地 PostgreSQL、演示数据和可用的 LLM 凭证；本轮已验证合同、切换逻辑、数据库路径与前端构建。
