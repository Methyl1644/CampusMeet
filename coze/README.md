# coze/ — CampusMate AI 智能体与算法资产（成员 D）

本目录是成员 D（智能体与算法）的全部交付物：Coze 工作流设计、Prompt、输入输出 Schema、评测集、演示数据与集成说明。

## 目录结构

```
coze/
├── README.md                          # 本文件
├── INTEGRATION.md                     # Coze ↔ 后端 ↔ 前端 对接总说明（C 接入时必读）
├── workflows/                         # 工作流设计文档（画布节点、异常处理、测试样例）
│   ├── 01_post_draft.md               # 工作流① AI 对话式发帖（P0 / F03）
│   ├── 02_classify_review.md          # 工作流② 分类与审核（P0 / F06）
│   ├── 03_match_teammates.md          # 工作流③ 智能匹配（P1 / F13）
│   ├── 04_team_plan.md                # 工作流④ 成队规划（P0 / F12）
│   └── 05_official_activity_extract.md# 工作流⑤ 官方活动抽取（P1 可选，不阻塞 P0）
├── prompts/                           # 提示词资产
│   ├── system_rules.md                # 公共系统规则（所有工作流前置拼接）
│   ├── safety_rules.md                # 安全规则（与后端 security.py 对齐）
│   ├── post_draft_prompt.md
│   ├── classify_review_prompt.md
│   ├── match_teammates_prompt.md
│   └── team_plan_prompt.md
├── schemas/                           # 工作流输入输出 JSON Schema（契约权威定义）
│   ├── post_draft.input.json          / post_draft.output.json
│   ├── classify_review.input.json     / classify_review.output.json
│   ├── match_teammates.input.json     / match_teammates.output.json
│   └── team_plan.input.json           / team_plan.output.json
├── evals/                             # 评测集（JSONL，每行一条用例）
│   ├── post_draft_cases.jsonl         # 20 条
│   ├── classify_review_cases.jsonl    # 20 条
│   ├── match_teammates_cases.jsonl    # 15 条
│   ├── team_plan_cases.jsonl          # 10 条
│   └── safety_cases.jsonl             # 20 条（安全专项）
└── examples/
    └── demo_xiaowang_mcm.json         # 演示数据：小王美赛完整链路（docs/demo-script.md）
```

## 四个 P0 工作流一览

| 工作流 | 后端工具 | 前端触点 | 环境变量 |
|--------|---------|---------|---------|
| ① AI 对话式发帖 | `ai_post_draft` | `POST /api/agent/post-draft` | `COZE_WORKFLOW_POST_DRAFT` |
| ② 分类与审核 | `ai_classify_review` | `POST /api/agent/classify-review` | `COZE_WORKFLOW_CLASSIFY_REVIEW` |
| ③ 智能匹配 | `ai_match_teammates` | `POST /api/agent/match` | `COZE_WORKFLOW_MATCH` |
| ④ 成队规划 | `ai_team_plan` | `POST /api/agent/team-plan` | `COZE_WORKFLOW_TEAM_PLAN` |

## 契约权威来源与当前状态

应用层契约的优先级：**`packages/shared/src/types.ts` + `src/api/agent.py` + `docs/d-ai-contract.md` > Coze 内部丰富 Schema**。Coze 可以在内部使用更多推理字段，但入口和出口必须转换为已冻结的应用契约。

**当前状态（2026-09-02）**：B 的 React 前端和 C 的 FastAPI 路由/安全引擎已上传 `main`；D 已完成四接口对账和 fallback 自动化验证。Coze workflow ID 仍可留空，不影响演示。匹配工作流在受控上下文查询完成前应继续使用后端 fallback。

## 评测集说明

每条用例字段：`id` / `task_type` / `input` / `expected_output` / `pass_criteria` / `risk_label`。

- `expected_output` 给出关键字段的期望值（不必全量）；
- `pass_criteria` 用自然语言描述可机器化的断言，供评测脚本逐条判定；
- 覆盖场景：美赛、挑战杯、编程项目、课程作业、学习搭子、体育活动、缺失关键信息、含联系方式、含隐私信息、高风险线下/金钱交易。

通过标准对齐 `docs/test-cases.md` §12：主分类准确率 ≥ 85%、核心字段提取 ≥ 80%、缺失字段识别率 ≥ 75%、风险内容召回率 ≥ 90%、Top-3 命中 ≥ 70%。

## 校验

修改任何 JSON / JSONL 后执行：

```bash
python -m json.tool coze/examples/demo_xiaowang_mcm.json > /dev/null
for f in coze/schemas/*.json; do python -m json.tool "$f" > /dev/null || echo "FAIL $f"; done
for f in coze/evals/*.jsonl; do while IFS= read -r line; do echo "$line" | python -m json.tool > /dev/null || echo "FAIL $f"; done < "$f"; done
```
