# CampusMeet Audit And UX Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve the actionable security findings and make the primary discovery, post-entry, personal-management, and publishing workflows clear and resilient.

**Architecture:** Harden existing FastAPI boundaries without changing the authentication protocol, then improve the React application through existing routes and components. Keep each batch independently testable and avoid the high-risk JWT-to-cookie migration during this pass.

**Tech Stack:** FastAPI, SQLAlchemy, React 18, React Router, TypeScript, Vitest, pytest, Render.

**Spec:** `C:/Users/裴斐/Downloads/梧桐遇CampusMeet-安全与质量审计报告.md` and `C:/Users/裴斐/Downloads/问题总清单.md`

## Global Constraints

- Preserve existing authentication, moderation, CORS allowlisting, and upload trust boundaries that the audit verified as working.
- Never expose verification codes unless `AUTH_TEST_MODE` is explicitly enabled.
- Trust proxy headers only when `TRUST_PROXY_HEADERS` is explicitly enabled.
- Bound all public list inputs before they reach database queries.
- Keep anonymous health checks minimal because Render requires `/health`.
- Preserve all user-authored changes already present in the worktree.

## Review Focus

- Missing mail configuration must fail closed without leaking a code.
- Spoofed forwarding headers must not bypass network rate limits when proxy trust is disabled.
- Login abuse must be limited for both existing and unknown accounts without account enumeration.
- Production must not expose API schema or internal readiness details.
- Publishing must retain the draft and clearly state that navigation can be interrupted while the request is running.

---

### Task 1: Authentication And Abuse Controls

**Files:**
- Modify: `src/utils/email_sender.py`
- Modify: `src/api/auth.py`
- Modify: `src/tools/auth_tools.py`
- Modify: `src/services/abuse_monitoring.py`
- Create: `src/utils/request_client.py`
- Test: `tests/test_auth_verification_flow.py`
- Test: `tests/test_abuse_monitoring.py`
- Test: `tests/test_request_client.py`

**Interfaces:**
- Produces: `client_network_identifier(request: Request) -> str`
- Produces: fail-closed email delivery and login cooldown responses.

- [x] Add failing tests for code leakage, trusted proxy extraction, spoofed header rejection, unknown-account login bursts, and uniform credential errors.
- [x] Implement explicit test-mode delivery and trusted-proxy client extraction.
- [x] Add login decisions to abuse monitoring and record attempts before account lookup.
- [x] Run the focused authentication and abuse test suite.

### Task 2: API Surface And Response Hardening

**Files:**
- Modify: `src/main.py`
- Modify: `src/api/posts.py`
- Modify: `src/tools/post_tools.py`
- Modify: `packages/shared/src/constants.ts`
- Test: `tests/test_production_config.py`
- Test: `tests/test_list_pagination_contract.py`
- Test: `apps/web/src/api/management.test.ts`

**Interfaces:**
- Produces: production-only OpenAPI disabling, security headers, bounded post list pagination, and correct operator metrics paths.

- [x] Add failing tests for production docs, security headers, and `page_size <= 40`.
- [x] Configure FastAPI documentation URLs from `APP_ENV` and add security headers middleware.
- [x] Bound post list query inputs at both API and tool layers.
- [x] Replace `/api/operations/*` frontend paths with `/api/operators/*` and run contract tests.

### Task 3: Frontend Accessibility And Loading Cost

**Files:**
- Modify: `apps/web/index.html`
- Modify: `apps/web/src/main.tsx`
- Modify: `apps/web/src/index.css`
- Modify: `apps/web/tailwind.config.js`
- Modify: `apps/web/src/pages/Login.tsx`
- Test: `apps/web/src/design/theme-contract.test.ts`

**Interfaces:**
- Produces: zoom-enabled viewport, system font stack, and corrected login contrast.

- [x] Update contract tests for the accessible viewport and zero-download system fonts.
- [x] Remove bundled Noto font imports and update the UI/title font stacks.
- [x] Raise the campus motto contrast while preserving the project palette.
- [x] Build the frontend and compare generated asset sizes (704.69 KB to 449.07 KB entry JS).

### Task 4: Navigation, Entry Clarity, And Error Recovery

**Files:**
- Modify: `apps/web/src/router/index.tsx`
- Create: `apps/web/src/pages/RouteError.tsx`
- Modify: `apps/web/src/components/explore/GroupCard.tsx`
- Modify: `apps/web/src/components/explore/ActivityCard.tsx`
- Modify: `apps/web/src/components/navigation/UserMenu.tsx`
- Test: `apps/web/src/components/explore/ExploreCards.test.tsx`
- Test: `apps/web/src/router/personalRoutes.test.ts`

**Interfaces:**
- Produces: branded route error/404 page, visible detail actions, and direct personal-management links.

- [x] Add tests for card detail affordances, personal management entries, and route errors.
- [x] Add root `errorElement` and a catch-all 404 route.
- [x] Make every discovery card expose a visible “查看详情” action while retaining full-card keyboard navigation.
- [x] Rename and group personal menu entries around “我的发布” and “我的组队”.

### Task 5: Publishing Continuity Feedback

**Files:**
- Modify: `apps/web/src/pages/Publish.tsx`
- Modify: `apps/web/src/components/publish/PublishReview.tsx`
- Modify: `apps/web/src/components/publish/publish.css`
- Test: `apps/web/src/pages/Publish.test.tsx`

**Interfaces:**
- Produces: explicit publish stages, elapsed-time reassurance, duplicate-submit protection, and browser navigation warning.

- [x] Add tests for progress copy, retained drafts, duplicate prevention, and unload warning.
- [x] Show ordered publish stages instead of a single indefinite “正在发布”.
- [x] Warn before browser navigation while publishing and explain that the request continues safely.
- [x] Preserve the idempotent request ID and restore the review state after recoverable failure.

### Task 6: Verification And Deferred-Risk Record

**Files:**
- Modify: `docs/superpowers/plans/2026-09-20-audit-and-ux-hardening.md`

**Interfaces:**
- Produces: reproducible verification evidence and a clearly scoped follow-up list.

- [x] Run focused backend and frontend tests after each task.
- [x] Run full pytest (560 passed, 1 skipped), Vitest (231 passed), TypeScript, and production build checks.
- [x] Record and repair stale migration, OpenAPI, and time-sensitive test baselines separately.
- [x] Defer cookie-session migration, dark mode, and hosting-level soft-404 policy to isolated follow-up work because each changes deployment or authentication architecture.
