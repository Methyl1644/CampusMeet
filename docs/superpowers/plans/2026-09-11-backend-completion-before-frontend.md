# CampusMate Backend Completion Before Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete CampusMate's backend business loops, production safeguards, and stable API contract before adapting the frontend, so frontend work is performed once against verified behavior.

**Architecture:** Deliver the backend as one milestone through small sequential branches. Establish migrations and request contracts first, implement identity and content governance next, complete collaboration and AI workflows after that, then freeze OpenAPI and response examples. Frontend implementation begins only after the backend completion gate passes.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL/Neon, pytest, Coze deployed workflows, Render.

**Related Plans:**
- `docs/superpowers/plans/2026-09-11-content-risk-governance.md`
- `docs/superpowers/plans/2026-09-11-official-identity-and-responsible-accounts.md`
- `docs/superpowers/plans/2026-09-11-tag-governance.md`
- `docs/superpowers/plans/2026-09-11-resource-permissions.md`

## Global Constraints

- This milestone changes backend code, migrations, tests, deployment configuration, and API documentation only.
- Do not redesign frontend pages while backend contracts are still changing.
- Each phase must keep existing REST endpoints operational or provide an explicit documented migration.
- All write operations must authenticate, authorize, validate, moderate where applicable, and be idempotent where retries are expected.
- Production data changes use Alembic migrations and are tested against PostgreSQL semantics.
- Coze is an optional semantic processor; database authority, permissions, enforcement, and fallback behavior remain in the backend.
- Every list endpoint added in this milestone is paginated and permission filtered.
- API errors use one stable structure and never expose stack traces, secrets, private evidence, or unrestricted user data.

## Phase 1: Database and API Foundation

**Files:**
- Create: `alembic.ini`
- Create: `migrations/env.py`
- Create: `migrations/versions/20260911_00_baseline.py`
- Modify: `src/storage/database/db.py`
- Modify: `src/main.py`
- Create: `src/api/schemas/`
- Modify: `src/api/common.py`
- Create: `tests/test_migrations.py`
- Create: `tests/test_api_contract.py`

- [x] Introduce a production-safe Alembic baseline and test upgrades from the current deployed schema.
- [x] Replace startup-time compatibility SQL with explicit migrations after the production schema is upgraded.
- [x] Add missing foreign keys and indexes for posts, applications, conversations, messages, teams, and team members.
- [x] Add unique constraints for one active application per applicant/post and one conversation per accepted application.
- [x] Introduce Pydantic request/response schemas, field length limits, enum validation, and consistent timestamps.
- [x] Standardize success and error envelopes and map domain conflicts to 409 instead of generic success/error text.
- [x] Add pagination metadata to applications, conversations, messages, tag proposals, organization reviews, and audit queues.
- [ ] Verify SQLite unit tests and PostgreSQL migration/integrity tests.

External gate: SQLite and PostgreSQL-dialect tests pass locally; a real PostgreSQL/Neon copy must still be exercised before launch.

## Phase 2: Authentication and Production Configuration

**Files:**
- Modify: `src/utils/auth.py`
- Modify: `src/tools/auth_tools.py`
- Modify: `src/api/auth.py`
- Modify: `src/utils/runtime.py`
- Modify: `.env.example`
- Modify: `render.yaml`
- Create: `tests/test_auth_lifecycle.py`
- Create: `tests/test_production_config.py`

- [x] Add password change and verification-code-based password reset flows with separate code purposes.
- [x] Add token identifiers and server-side revocation for logout, password reset, account restriction, and compromised sessions.
- [x] Preserve short access-token lifetime or add a rotated refresh-token flow; never store reusable tokens in logs.
- [x] Apply rate limits to verification-code requests, login attempts, registration, and password reset.
- [x] Fail production startup when JWT, database, campus domains, email delivery, or test-mode settings are unsafe.
- [x] Keep `/health` as liveness and add `/ready` for database and required-configuration readiness.
- [x] Add account deactivation and privacy-safe data export/deletion request states without deleting audit evidence immediately.

## Phase 3: Official Identity and Scoped Responsibility

**Plan:** Execute backend Tasks 1-6 from `2026-09-11-official-identity-and-responsible-accounts.md`.

- [x] Complete organization evidence, applicant status, operator queue, review reasons, renewal, and expiry.
- [x] Replace direct organization member activation with invite, accept, decline, revoke, and ownership transfer.
- [x] Add secure platform operator management after the bootstrap operator.
- [x] Preserve topic roles `manager`, `editor`, and `coordinator` as event-specific grants.
- [x] Preserve post roles `editor` and `application_manager` as post-specific grants.
- [x] Return derived identity/permission summaries and public trust badges without leaking evidence.
- [x] Verify expiry and revocation at every protected write endpoint, not only in UI visibility.

## Phase 4: Content Risk Governance and Operator Cases

**Plan:** Execute backend Tasks 1-7 from `2026-09-11-content-risk-governance.md`.

- [x] Add the unified `allow`, `revise`, `review`, and `block` moderation decision service.
- [x] Screen every AI drafting turn before Coze and screen generated text before returning it.
- [x] Apply surface-specific moderation to posts, topics, applications, and temporary chat.
- [x] Add reports, user blocks, moderation cases, account restrictions, operator resolution, and appeals.
- [x] Add behavioral abuse monitoring for spam, repeated bypass attempts, mass applications/messages, and coordinated reporting.
- [x] Store masked moderation evidence and structured rule IDs without duplicating full private content.
- [x] Add moderation latency, result, fallback, backlog, and appeal metrics.

## Phase 5: Complete Post and Application Lifecycles

**Files:**
- Modify: `src/api/posts.py`
- Modify: `src/tools/post_tools.py`
- Modify: `src/api/applications.py`
- Modify: `src/tools/application_tools.py`
- Modify: `src/storage/database/models/post.py`
- Modify: `src/storage/database/models/application.py`
- Create: `tests/test_post_lifecycle.py`
- Create: `tests/test_application_lifecycle.py`

- [x] Add post close, reopen, archive, and soft-delete operations with owner/scoped-manager authorization.
- [x] Add deadline-aware automatic closure while keeping historical applications and teams readable.
- [x] Add applicant withdrawal before acceptance and prohibit withdrawal after a team is confirmed.
- [x] Make create, accept, reject, and withdraw transitions transactional and idempotent under retries.
- [x] Prevent duplicate active applications and reject new applications when the team is full or deadline has passed.
- [x] Update member counts and recruitment status through one domain service instead of scattered assignments.
- [x] Add audit events for all lifecycle transitions.

## Phase 6: Complete Conversation and Team Management

**Files:**
- Modify: `src/api/messages.py`
- Modify: `src/tools/message_tools.py`
- Modify: `src/api/teams.py`
- Modify: `src/tools/team_tools.py`
- Modify: `src/storage/database/models/conversation.py`
- Modify: `src/storage/database/models/team.py`
- Create: `tests/test_conversation_lifecycle.py`
- Create: `tests/test_team_management.py`

- [x] Make bilateral team confirmation concurrency safe and idempotent using transactions and database constraints.
- [x] Add message pagination, read state, unread counts, and server-enforced blocked-user rules.
- [x] Preserve contact unlocking only after bilateral confirmation and recheck access on every team-detail request.
- [x] Add team task create, edit, assign, reorder, complete, and delete operations.
- [x] Add team role editing, member leave/remove, ownership transfer, and team close/archive operations.
- [x] Define what happens to a recruiting post when a member leaves or the team reaches capacity.
- [x] Keep polling for the first stable release; defer WebSocket delivery until the REST lifecycle is complete.

## Phase 7: Complete Coze Workflows 3 and 4

**Files:**
- Modify: `src/tools/ai_tools.py`
- Modify: `src/api/agent.py`
- Modify: `.env.example`
- Modify: `render.yaml`
- Modify: `docs/d-ai-contract.md`
- Create: `tests/test_match_workflow.py`
- Create: `tests/test_team_plan_workflow.py`

- [x] Add `COZE_MATCH_API_URL` and `COZE_TEAM_PLAN_API_URL` deployed-endpoint support using the existing backend-only API token.
- [x] Build a controlled match context in the backend containing only candidate IDs, skills, availability, and permitted profile fields.
- [x] Never allow Coze to query unrestricted users or receive private contacts, passwords, evidence, messages, or email addresses.
- [x] Validate returned match IDs against the supplied candidate set, clamp scores, limit results, and provide deterministic fallback ranking.
- [x] Build a controlled team-plan context from current members, approved roles, post requirements, and existing tasks.
- [x] Validate the workflow 4 result and persist it transactionally; the current deployed-success path must not return without saving.
- [x] Add timeout, malformed-output, unauthorized-ID, duplicate-task, and fallback tests.

## Phase 8: Evidence and Media Uploads

**Files:**
- Create: `src/api/uploads.py`
- Create: `src/services/uploads.py`
- Modify: `src/main.py`
- Modify: `src/storage/s3/s3_storage.py`
- Modify: `.env.example`
- Modify: `render.yaml`
- Create: `tests/test_upload_security.py`

- [x] Add authenticated presigned-upload creation and completion endpoints.
- [x] Restrict MIME types, extensions, size, key prefixes, and ownership for avatars, topic covers, and private organization evidence.
- [x] Keep private evidence in a non-public prefix and issue short-lived reviewer download URLs only to authorized operators.
- [x] Validate uploaded object metadata before attaching it to an application or profile.
- [x] Add deletion/retention handling for abandoned uploads, rejected evidence, and replaced avatars/covers.
- [x] Add Render-compatible `OBJECT_STORAGE_ENDPOINT`, `OBJECT_STORAGE_REGION`, `OBJECT_STORAGE_BUCKET`, `OBJECT_STORAGE_ACCESS_KEY`, and `OBJECT_STORAGE_SECRET_KEY` settings; do not depend on Coze workload identity outside Coze.
- [x] Add a local test storage adapter so upload tests do not require production S3 credentials.

## Phase 9: Notifications and Scheduled Maintenance

**Files:**
- Create: `src/storage/database/models/notification.py`
- Create: `src/api/notifications.py`
- Create: `src/services/notifications.py`
- Create: `src/jobs/maintenance.py`
- Modify: `src/main.py`
- Create: `tests/test_notifications.py`
- Create: `tests/test_maintenance_jobs.py`

- [x] Add durable notifications for application decisions, collaborator invitations, organization review, new messages, bilateral confirmation, reports, appeals, and expiring permissions.
- [x] Add list, unread-count, mark-read, and mark-all-read endpoints.
- [x] Emit notifications in the same transaction as the triggering domain event or through a transactional outbox.
- [x] Add idempotent maintenance jobs for expired grants, expired organization verification, expired recruitment, abandoned uploads, and notification retention.
- [ ] Run jobs through a dedicated Render worker or controlled scheduled command, never as an uncoordinated timer in every web instance.

External gate: the idempotent command is ready and documented. Render Cron Jobs have no free instance, so scheduling is intentionally deferred until a paid scheduler is approved.

## Phase 10: Operations, Observability, and Recovery

**Files:**
- Modify: `src/main.py`
- Modify: `src/api/common.py`
- Create: `src/api/operations.py`
- Modify: `docs/deployment/render-neon.md`
- Create: `docs/operations/backend-runbook.md`
- Create: `tests/test_observability.py`

- [x] Add request IDs and structured logs for authentication, moderation, identity, collaboration, database, email, and Coze calls.
- [x] Redact authorization headers, tokens, passwords, verification codes, contact details, evidence, and message bodies.
- [x] Add metrics for endpoint latency/errors, database pool exhaustion, email failures, Coze timeout/fallback, moderation decisions, and queue backlog.
- [x] Add operator audit search with pagination and strict authorization.
- [x] Document backup, restore, migration rollback, key rotation, Coze outage, email outage, and account-compromise procedures.
- [ ] Verify Neon backups and perform one restore rehearsal before production launch.

External gate: the rehearsal procedure is documented in `docs/operations/backend-runbook.md` and requires access to the live Neon project.

## Phase 11: Backend Contract Freeze

**Files:**
- Create: `docs/api/openapi.json`
- Create: `docs/api/backend-contract.md`
- Modify: `packages/shared/src/types.ts`
- Modify: `packages/shared/src/constants.ts`
- Modify: `docs/e2e-checklist.md`
- Create: `tests/test_openapi_snapshot.py`

- [x] Export and commit the verified OpenAPI schema after all backend phases pass.
- [x] Document every endpoint's authorization, request, response, pagination, errors, side effects, and idempotency behavior.
- [x] Generate or mechanically align shared TypeScript request/response types from the frozen schema.
- [x] Add an OpenAPI snapshot test so accidental contract changes fail CI.
- [x] Provide representative fixtures for visitor, campus user, organization owner, publisher, topic manager, post manager, team member, and operator.
- [ ] Run complete backend tests, PostgreSQL integration tests, migration tests, and deployed smoke tests.

External gate: local backend and migration tests pass; real Neon and post-deploy Render smoke tests remain.

## Backend Completion Gate

Frontend implementation begins only when all of the following are true:

- [ ] All Phases 1-11 are complete or an explicitly deferred feature is removed from the first-release product scope.
- [ ] Database migrations upgrade a copy of the current production schema successfully.
- [ ] All backend tests pass against the supported Python version and PostgreSQL behavior.
- [ ] Render `/health` and `/ready` pass after deployment.
- [x] Workflows 1-4 pass safe, malformed, timeout, and fallback test cases.
- [x] Identity, permissions, moderation, report/appeal, application, conversation, and team lifecycle smoke tests pass.
- [x] No secrets or private evidence appear in logs or public API responses.
- [x] `docs/api/openapi.json` and shared TypeScript types are frozen at the same commit.
- [x] The frontend team receives the contract document, fixtures, environment variables, and endpoint readiness matrix.

## Frontend Handoff Order

After the completion gate, configure frontend in this order:

1. Authentication, profile identity summary, and permission-aware navigation.
2. Organization verification and operator review.
3. Topic/post creation, scoped responsible-person management, and moderation feedback.
4. Applications, messages, bilateral confirmation, and team management.
5. Notifications, reports, blocks, appeals, and operator queues.
6. Coze matching and team planning, including timeout and manual fallback states.
