# 成员 D 智能体 fallback 验证报告

> 验证日期：2026-09-02
> 验证分支：`feat/d-final-integration`
> 验证原则：不使用真实 Coze Token/ID，用可重复的本地边界替身隔离外部 LLM/HTTP，保留真实工具、数据库查询、路由拆包和持久化逻辑。

## 1. 验证范围

| 能力 | 未配置 Coze 时的路径 | 关键断言 | 结果 |
|------|-----------------------|----------|------|
| AI 对话式发帖 | LLM fallback | 返回 `reply/draft/is_complete` | 通过 |
| AI 分类审核 | LLM fallback | 返回分类、标签、风险、建议 | 通过 |
| AI 队友匹配 | 数据库 + LLM fallback | 查询非帖主认证用户，返回 `user_id/score/reason` | 通过 |
| AI 成队规划 | 数据库 + LLM fallback | 返回分工/议程/任务/风险，并写回 `teams` 表 | 通过 |
| Coze 切换 | 规范 workflow 环境变量 | 四个工具配置后均优先走 Coze | 通过 |

## 2. 自动化命令

```powershell
python -m pytest -q tests/test_d_ai_fallback.py
python -m pytest -q
```

第一条专项覆盖 8 个场景：4 个规范 Coze 环境变量切换 + 4 个 fallback 行为。完整套件还覆盖 C 的 API 外壳、脱敏、匹配拆包和成队规划拆包。

## 3. 结论与边界

- Coze 额度不足不会阻塞四条 AI 主链路。
- `COZE_WORKFLOW_MATCH` 当前应留空，直到工作流完成受控、已脱敏的上下文查询。
- 本报告证明结构化切换、数据库路径和合同字段正确；真实线上模型质量仍需使用 `coze/evals/*.jsonl` 进行独立评测。
