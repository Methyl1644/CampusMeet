# Render + Neon Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy CampusMate's existing Vite frontend and FastAPI backend on Render with Neon PostgreSQL and production-safe verification email.

**Architecture:** Add small environment-parsing helpers to the existing runtime and database modules, add a Resend HTTPS transport ahead of the existing SMTP transport, and describe the two Render services in a root Blueprint. Keep secrets in Render and preserve all existing local-development fallbacks.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, PostgreSQL/Neon, React/Vite, Render Blueprint, Resend HTTPS API

**Spec:** `docs/superpowers/specs/2026-09-10-render-neon-deployment.md`

## Global Constraints

- Never commit a credential, database URL, JWT secret, or API token.
- Preserve the current uncommitted backend integration work in shared files.
- Keep SQLite and SMTP available for local development.
- Use the Neon pooled URL as `DATABASE_URL` in production.
- Do not enable the Coze agent runtime on Render unless workload identity credentials exist.

---

### Task 1: Runtime and database deployment settings

**Files:**
- Modify: `src/utils/runtime.py`
- Modify: `src/main.py`
- Modify: `src/storage/database/db.py`
- Test: `tests/test_render_deployment.py`

**Interfaces:**
- Produces: `get_allowed_origins(environment=None) -> list[str]`
- Produces: `get_postgres_pool_options(environment=None) -> dict[str, int | bool]`
- Consumes: `FRONTEND_ORIGINS`, `FRONTEND_ORIGIN`, `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`

- [x] Write tests that require normalized configured origins, local defaults, and a small PostgreSQL pool.
- [x] Run `pytest tests/test_render_deployment.py -q` and confirm the new assertions fail because the helpers do not exist.
- [x] Implement the helpers and wire them into FastAPI CORS and SQLAlchemy engine creation.
- [x] Run the focused test and the existing authentication/content tests. The content suite passes; authentication awaits the full local dependency environment.
- [x] Commit boundary prepared with runtime/database files and their tests.

### Task 2: Resend verification email transport

**Files:**
- Modify: `src/utils/email_sender.py`
- Modify: `.env.example`
- Test: `tests/test_render_deployment.py`

**Interfaces:**
- Consumes: `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, `RESEND_API_BASE_URL`
- Produces: the existing `send_verification_email(to_email, code, purpose)` result contract

- [x] Add tests with an injected fake HTTPS opener that assert the Resend endpoint, authorization header, sender, recipient, and absence of the code from logs/results.
- [x] Run the focused test and confirm failure because no Resend transport exists.
- [x] Implement the HTTPS request with the Python standard library, preferring Resend when its API key and sender are configured and retaining SMTP otherwise.
- [x] Document the new variables in `.env.example` without values.
- [x] Run focused and authentication tests and prepare the email/config/test commit boundary.

### Task 3: Render Blueprint and operator guide

**Files:**
- Create: `render.yaml`
- Create: `.python-version`
- Create: `docs/deployment/render-neon.md`
- Test: `tests/test_render_deployment.py`

**Interfaces:**
- Backend service: `campusmate-api`, health path `/health`, region `singapore`
- Frontend service: `campusmate-web`, repository-root build, publish path `apps/web/dist`

- [x] Add contract tests for service runtimes, build/start commands, secret placeholders, generated JWT secret, frontend API URL, and SPA rewrite.
- [x] Run the focused test and confirm failure because the deployment artifacts do not exist.
- [x] Add the Blueprint, Python version pin, and exact dashboard instructions for the user's already-created Neon database.
- [x] Run deployment contract tests and inspect the Blueprint for accidental secrets.
- [x] Prepare deployment artifacts and their tests for the release commit.

### Task 4: Full verification and handoff

**Files:**
- Verify only; modify production files only if a failing test exposes a defect.

**Interfaces:**
- Consumes all artifacts from Tasks 1-3.
- Produces a deployment-ready branch and a list of secret values the user must enter directly in Render.

- [x] Run the complete backend test suite (59 passed).
- [x] Run frontend contract tests (24 passed) and TypeScript checking.
- [x] Run the frontend production build.
- [x] Verify no tracked file contains a Neon hostname, password, or non-placeholder API token.
- [x] Review the final diff against the specification and independent release review.
