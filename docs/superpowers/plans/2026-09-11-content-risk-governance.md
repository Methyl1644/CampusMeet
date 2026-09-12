# CampusMate Content Risk Governance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent unsafe invitations, discriminatory requirements, fraud, illegal activity, privacy leakage, harassment, and platform-bypass behavior from entering CampusMate's AI drafting, posts, applications, or temporary chats, while preserving an auditable manual-review and appeal path.

**Architecture:** The backend is the final policy authority. A deterministic rule layer normalizes text and catches explicit violations, Coze workflow 2 may add semantic risk signals, and a single moderation service merges both into `allow`, `revise`, `review`, or `block`. Every enforcement point uses that service before persistence. Decisions that affect publication or accounts are stored for operator review; AI output alone cannot ban a user, approve an appeal, or grant permissions.

**Tech Stack:** FastAPI, SQLAlchemy, PostgreSQL/SQLite, Pydantic, pytest, existing Coze deployed workflow integration.

**Spec:** `docs/prd.md`, `docs/user-flow.md`, `docs/d-ai-contract.md`, and `docs/superpowers/specs/2026-09-11-tag-governance-and-resource-permissions-design.md`.

## Global Constraints

- Never send passwords, verification evidence, private contact details, or unrestricted user records to Coze.
- Do not rely on a raw keyword hit as the sole reason for an account restriction.
- Block explicit illegal, exploitative, sexual solicitation, fraud, threat, or private-location content before Coze and before database persistence.
- Treat protected or personal attributes as contextual: legitimate activity requirements may be reviewed, while dating-oriented, appearance-based, or exclusionary recruitment is revised or blocked.
- Contact details remain unavailable before bilateral team confirmation; attempts to bypass this rule are rejected and audited.
- User-facing errors explain what must be changed without exposing the complete detection rule set.
- Moderation endpoints require operator authorization and write an `AuditLog` entry.
- All schema changes use versioned migrations; startup must no longer be the primary schema-upgrade mechanism.

---

## Task 1: Establish the Moderation Decision Contract

**Files:**
- Create: `src/services/content_moderation.py`
- Modify: `src/utils/security.py`
- Create: `tests/test_content_moderation.py`

- [x] **Step 1: Add failing tests for normalization and explicit rules**

Cover whitespace and punctuation variants, split contact details, URL/QR/off-platform language, hotels and private rooms, dating or paid-companionship requests, sexual content, threats, fraud, illegal services, doxxing, discriminatory appearance/gender requirements, spam, and legitimate counterexamples such as a women's sports event or a safety notice mentioning a hotel.

- [x] **Step 2: Define one stable decision shape**

Add `ModerationDecision` with:

```python
action: Literal["allow", "revise", "review", "block"]
risk_level: Literal["low", "medium", "high", "critical"]
rule_ids: list[str]
user_message: str
suggestions: list[str]
cleaned_text: str
```

Add a `ModerationContext` containing `surface`, `user_id`, `conversation_id`, `contact_unlocked`, and optional structured fields. Keep existing `ScreenResult` compatibility until all callers are migrated.

- [x] **Step 3: Implement normalized and compound-rule evaluation**

Normalize full-width characters, spacing, common obfuscation, repeated punctuation, and URL forms. Implement compound rules so combinations such as private venue plus dating intent escalate beyond either phrase alone. Keep stable rule IDs in code and map them to concise Chinese user messages.

- [x] **Step 4: Verify the unit suite**

Run:

```powershell
pytest tests/test_content_moderation.py -q
```

Expected: all normalization, violation, escalation, and legitimate-context cases pass.

## Task 2: Gate AI Drafting Before Any Coze Call

**Files:**
- Modify: `src/api/agent.py`
- Modify: `src/tools/ai_tools.py`
- Modify: `packages/shared/src/types.ts`
- Create: `tests/test_post_draft_moderation.py`
- Modify: `tests/test_d_ai_fallback.py`

- [x] **Step 1: Add failing tests proving unsafe text never reaches Coze**

Patch the deployed-workflow caller and assert it is not invoked for blocked input. Add cases for first-turn and later-turn messages, because a safe opening message can be followed by unsafe details.

- [x] **Step 2: Moderate the current message and accumulated draft**

Call the moderation service before `ai_post_draft`. Return a structured response with `blocked: true`, the action, risk level, user message, and suggestions. Preserve the previous safe draft without inserting the rejected text.

- [x] **Step 3: Validate AI output before returning it**

Run the same service against generated free-text fields. Reject unsafe model output and fall back to the last safe draft. Do not allow the model to lower a rule-based risk level.

- [x] **Step 4: Verify endpoint behavior**

Run:

```powershell
pytest tests/test_post_draft_moderation.py tests/test_d_ai_fallback.py -q
```

Expected: blocked inputs do not call Coze, safe multi-turn extraction still works, and the response contract remains compatible with the publish page.

## Task 3: Apply the Same Policy to Every Persisted User Surface

**Files:**
- Modify: `src/api/posts.py`
- Modify: `src/tools/application_tools.py`
- Modify: `src/tools/message_tools.py`
- Modify: `src/api/applications.py`
- Modify: `src/api/messages.py`
- Create: `tests/test_surface_moderation.py`

- [x] **Step 1: Add failing tests for posts, applications, and messages**

Test create and update, application fields, and temporary-chat messages. Include contact details before and after `contact_unlocked`, and verify no rejected content is committed.

- [x] **Step 2: Enforce surface-specific policy**

Use strict public-post rules for post and application text. In temporary chat, reject contact details before bilateral confirmation and permit ordinary contact exchange after confirmation. Always block critical threats, exploitation, fraud, and illegal content regardless of team status.

- [x] **Step 3: Add request schemas and length limits**

Replace raw `dict[str, Any]` bodies touched in this task with Pydantic request models. Reject empty messages, oversized text, invalid status values, and malformed lists with normal 422 responses.

- [x] **Step 4: Verify persistence boundaries**

Run:

```powershell
pytest tests/test_surface_moderation.py tests/test_post_publish_review.py tests/test_team_confirmation.py -q
```

Expected: every persisted text surface is screened, existing post review still works, and bilateral contact unlocking is unchanged.

## Task 4: Introduce Versioned Database Migrations and Moderation Records

**Files:**
- Create: `alembic.ini`
- Create: `migrations/env.py`
- Create: `migrations/versions/20260911_01_moderation_foundation.py`
- Create: `src/storage/database/models/moderation.py`
- Modify: `src/storage/database/models/__init__.py`
- Modify: `src/storage/database/shared/model.py`
- Modify: `src/main.py`
- Create: `tests/test_migrations.py`

- [ ] **Step 1: Add migration smoke tests**

Test upgrade from an empty database and from the current production-compatible schema. Verify a second upgrade is idempotent.

- [ ] **Step 2: Add moderation tables**

Create:

```text
moderation_events: surface, target_type, target_id, actor_id, action,
                   risk_level, rule_ids, excerpt, source, status, created_at
reports: reporter_id, target_type, target_id, reason_code, description,
         status, assigned_operator_id, resolution, created_at, resolved_at
account_restrictions: user_id, restriction_type, reason_code, starts_at,
                      expires_at, created_by, revoked_at
```

Store only a short masked excerpt in moderation records. Do not duplicate full private messages into audit metadata.

- [ ] **Step 3: Adopt explicit migrations**

Run migrations as a deployment step. Keep `Base.metadata.create_all` only for isolated local/test bootstrap during the transition, then remove `ensure_compatibility_columns` after production has upgraded.

- [ ] **Step 4: Verify both databases**

Run migration and model tests against SQLite, then run the PostgreSQL integration job used by deployment checks.

## Task 5: Add Reporting, Blocking, Operator Review, and Appeals

**Files:**
- Create: `src/api/moderation.py`
- Create: `src/services/moderation_cases.py`
- Modify: `src/main.py`
- Modify: `src/services/permissions.py`
- Modify: `packages/shared/src/constants.ts`
- Modify: `packages/shared/src/types.ts`
- Create: `tests/test_moderation_cases.py`

- [ ] **Step 1: Add authorization and lifecycle tests**

Cover report creation, duplicate-report coalescing, operator queue access, assignment, resolution, temporary restriction, restriction expiry, appeal submission, and appeal review. Verify ordinary users cannot access operator data or restrict accounts.

- [ ] **Step 2: Implement user actions**

Add endpoints to report a post, topic, message, or user; block/unblock another user; list the current user's reports; and submit one appeal per resolved enforcement event.

- [ ] **Step 3: Implement operator actions**

Add paginated review queues, case detail, resolve/dismiss, content hide/restore, temporary account restriction, and appeal resolution. Every transition writes both the case history and `AuditLog`.

- [ ] **Step 4: Prevent blocked-user interactions**

Exclude blocked pairs from matching and prevent new applications or conversations between them. Preserve historical records for auditing without showing new notifications.

- [ ] **Step 5: Verify the complete case lifecycle**

Run:

```powershell
pytest tests/test_moderation_cases.py tests/test_resource_permissions.py -q
```

Expected: only operators can enforce platform-wide actions, resource coordinators remain limited to their own topics/posts, and appeals cannot silently restore content.

## Task 6: Detect Abuse Patterns Without Delegating Enforcement to AI

**Files:**
- Create: `src/services/abuse_monitoring.py`
- Modify: `src/api/common.py`
- Modify: `src/tools/auth_tools.py`
- Modify: `src/tools/application_tools.py`
- Modify: `src/tools/message_tools.py`
- Create: `tests/test_abuse_monitoring.py`

- [ ] **Step 1: Add behavioral-risk tests**

Cover verification-code bursts, failed logins, repeated identical posts/messages, rapid applications, repeated contact-sharing attempts, mass unsolicited messages, and coordinated reports. Include tests that ordinary active users do not trigger restrictions.

- [ ] **Step 2: Add server-side rate controls**

Apply per-account and per-IP windows to authentication, posting, applications, and messaging. Return a retry time, do not disclose whether a target account exists, and store only hashed network identifiers with a short retention period.

- [ ] **Step 3: Add progressive responses**

Use warning, temporary cooldown, manual review, and temporary restriction. Permanent restrictions always require an operator decision.

- [ ] **Step 4: Verify concurrency behavior**

Run tests with concurrent duplicate requests and confirm limits cannot be bypassed by racing two requests.

## Task 7: Harden Coze Integration and Moderation Observability

**Files:**
- Modify: `src/tools/ai_tools.py`
- Modify: `src/api/agent.py`
- Modify: `.env.example`
- Modify: `render.yaml`
- Modify: `docs/deployment/render-neon.md`
- Create: `tests/test_moderation_observability.py`

- [ ] **Step 1: Add failure and timeout tests**

Cover Coze timeout, malformed output, unknown rule IDs, risk downgrades, token errors, and retry exhaustion. Verify rule-based blocking still works when Coze is unavailable.

- [ ] **Step 2: Merge AI signals conservatively**

Accept only the documented schema. Coze may escalate risk or suggest review, but cannot override deterministic blocks, reveal hidden contacts, create tags, grant permissions, or restrict an account.

- [ ] **Step 3: Add structured operational signals**

Log request ID, surface, latency, result source, action, risk level, and rule IDs without storing full user text or API tokens. Add counters for allow/revise/review/block, false-positive appeals, Coze timeout, and degraded fallback.

- [ ] **Step 4: Add readiness checks and alerts**

Keep `/health` as liveness. Add `/ready` to verify database access and required production configuration. Treat Coze as degradable rather than a readiness blocker. Document alerts for elevated block rates, repeated timeouts, report backlog, and failed migrations.

## Task 8: End-to-End Release Gate

**Files:**
- Create: `tests/test_content_risk_e2e.py`
- Modify: `docs/e2e-checklist.md`
- Modify: `docs/test-cases.md`
- Modify: `docs/deployment/render-neon.md`

- [ ] **Step 1: Add a fixed adversarial test corpus**

Include direct, obfuscated, multi-turn, and compound-risk inputs plus legitimate near-neighbor examples. Version expected actions and rule IDs so policy changes are reviewed explicitly.

- [ ] **Step 2: Run the complete backend suite**

```powershell
pytest -q
```

Expected: all tests pass with no moderation data leaked in logs.

- [ ] **Step 3: Run production smoke tests**

Verify liveness, readiness, safe AI drafting, blocked unsafe drafting, safe post publication, blocked message before confirmation, allowed contact exchange after bilateral confirmation, report creation, operator resolution, restriction expiry, and appeal review.

- [ ] **Step 4: Roll out in observe-first mode**

For newly added non-critical semantic rules, record and review decisions before enabling automatic blocking. Explicit critical rules remain blocking from the first release. Compare operator outcomes and appeals before changing thresholds.

## Recommended Delivery Order

1. Tasks 1-3: close the immediate unsafe-content gap.
2. Task 4: establish reliable schema evolution before new governance data is added.
3. Tasks 5-6: complete the human-review and account-abuse loop.
4. Tasks 7-8: harden production operation and release safely.
