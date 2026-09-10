# Render + Neon Deployment Specification

## Goal

Make the existing CampusMate React/FastAPI application deployable as a public Render static site and Render web service backed by the user's Neon PostgreSQL project.

## Architecture

- Render Static Site builds `apps/web` and serves the Vite output.
- Render Web Service runs the FastAPI application from the repository root in the Singapore region.
- The frontend calls the public backend URL through `VITE_API_BASE_URL`.
- The backend connects to Neon through a pooled PostgreSQL URL stored only in `DATABASE_URL`.
- Verification email is sent through the Resend HTTPS API when configured, with the existing SMTP path retained for non-Render environments.
- Coze credentials remain optional backend-only secrets. The deterministic fallback remains available when workflow IDs are absent.

## Requirements

1. CORS origins must come from `FRONTEND_ORIGINS` or `FRONTEND_ORIGIN`, accept a comma-separated list, strip trailing slashes, and retain local Vite origins for development.
2. PostgreSQL must use a small configurable SQLAlchemy pool suitable for a serverless pooled database. SQLite behavior must remain unchanged.
3. Production email must support Resend over HTTPS without logging or returning the verification code. SMTP remains a fallback when explicitly configured.
4. `render.yaml` must define a free Singapore Python web service and a Vite static site, include an SPA rewrite, generate `JWT_SECRET`, and prompt for secrets instead of committing them.
5. The backend health check must remain `/health`; startup must bind to Render's `$PORT`.
6. The deployment guide must tell the operator exactly where to paste the Neon pooled URL and how to wire the frontend and backend URLs.
7. No credentials, database URLs, or API tokens may be written to tracked files.
8. Existing API routes, authentication behavior, content seeding, and AI fallbacks must not change.

## Acceptance

- Deployment configuration contract tests pass.
- Runtime, database, and email unit tests pass.
- Existing backend tests pass.
- Frontend tests, type checking, and production build pass.
- A local production-mode smoke test can start the API and return a healthy response without exposing credentials.
