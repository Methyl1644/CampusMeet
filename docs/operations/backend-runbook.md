# CampusMate Backend Runbook

## Service checks

- `GET /health` is a process liveness check. It must not depend on external AI or email services.
- `GET /ready` checks required production configuration and the database connection.
- Every response includes `X-Request-ID`. Use that value to correlate a user report with Render logs.
- `GET /api/operators/metrics` and `GET /api/operators/audit-logs` require an active platform operator role.

Do not paste authorization headers, verification codes, evidence, messages, email addresses, or phone numbers into tickets. Application logs redact these fields and only record method, path, status, duration, and structured outcome counters.

## Deploy and migrate

The Render start command runs migrations before starting the API:

```text
uv run --no-sync alembic upgrade head && uv run --no-sync python src/main.py -m http -p $PORT
```

Before deployment, take a Neon restore point or confirm the current branch restore window. Migrations are forward-only in production. If a migration fails, stop deployment, restore the database to the pre-deploy point when data was changed, and redeploy the previous application commit. Do not run an improvised downgrade against production.

## Scheduled maintenance

Run this command once per day from one controlled scheduler:

```text
uv run --no-sync python src/jobs/maintenance.py
```

The job is idempotent. It expires grants and organization verification, closes deadline-passed recruitment, abandons expired pending uploads, sends permission-expiry reminders, and removes old read notifications.

Render Cron Jobs are a paid service and do not have a free instance type. For the first release, run the command manually after deployment and daily during active testing, or create one paid Render Cron Job when continuous operation begins. Never start this timer in every web instance. See [Render Cron Jobs](https://render.com/docs/cronjobs).

## Backup and restore rehearsal

1. In Neon, confirm the production branch restore window and create a protected restore point before a risky migration.
2. Restore to a new temporary branch, never over the active production branch during rehearsal.
3. Point a temporary Render service or local read-only check at the restored branch.
4. Run `alembic current`, `/ready`, and representative read checks for users, posts, applications, teams, audit logs, and notifications.
5. Record the restore branch, timestamps, migration revision, row-count checks, and reviewer. Delete the temporary branch only after sign-off.

This rehearsal is an external launch gate and cannot be considered complete from repository tests alone.

## Key rotation

### JWT compromise

1. Replace `JWT_SECRET` in Render with a new random value.
2. Redeploy the API. All existing tokens become invalid immediately.
3. Review `/api/operators/audit-logs` for suspicious authentication and role events.
4. Ask affected users to reset passwords. Password reset revokes all server-side sessions.

### Coze token

1. Create a new Coze API token.
2. Replace `COZE_DEPLOY_API_TOKEN` in Render and redeploy.
3. Test workflows 1-4. Then revoke the old token in Coze.

### Brevo and object storage

Create a replacement key, update Render, redeploy, verify one operation, and revoke the old key. Never place old or new values in logs, screenshots, repository files, or chat.

## Dependency outages

### Coze outage or timeout

The backend validates Coze output and uses deterministic fallback behavior. Check the `coze.call` and fallback metrics, then test one drafting request. Do not disable moderation or permissions to restore AI functionality. Users can continue with manual post editing.

### Email outage

Registration and password reset that require new verification codes will be unavailable. Existing authenticated users remain usable. Check Brevo sender status, API key, quota, and `BREVO_FROM_EMAIL`; restore delivery and send a fresh code rather than exposing an old code.

### Database outage

`/health` may remain live while `/ready` fails. Pause writes, inspect Neon and connection-pool status, and avoid repeated deploys. After recovery, run `/ready`, migration revision checks, then one read and one reversible write smoke test.

## Account compromise

1. Suspend the affected platform role or scoped grant immediately.
2. Revoke the user's sessions and require password reset.
3. Review audit events by actor ID and time range.
4. Preserve masked moderation/audit evidence; do not delete it during account deactivation.
5. Rotate shared keys if the account could access Render, Coze, Brevo, Neon, or storage consoles.

## Upload incidents

Private organization evidence is stored under `private/organization-evidence` and can only be downloaded through a short-lived operator URL. Public avatars and topic covers are attached only after metadata verification. Abandoned pending uploads are cleaned by maintenance; replaced public media is deleted during attachment replacement.
