# CampusMate Backend Contract

The canonical machine-readable contract is `docs/api/openapi.json`. Regenerate it after an intentional API change with:

```text
python scripts/export_openapi.py
```

`tests/test_openapi_snapshot.py` rejects unreviewed contract drift.

## Common rules

- Public endpoints: `/health`, `/ready`, registration, login, code delivery, and password reset. Current first-release content discovery requires login.
- Authenticated endpoints require `Authorization: Bearer <token>`. Tokens expire within 24 hours and must also match an active server-side session.
- Operator endpoints require an active `operator` or `senior_operator` grant. Platform-role mutation additionally requires `senior_operator` where specified.
- IDs are returned as strings even when their database column is numeric.
- Timestamps are ISO 8601 strings with timezone where available.
- List data uses `{list,total,page,page_size,pages}`. `page` starts at 1; endpoint limits are recorded in OpenAPI.
- Success uses `{code:0,message,data}`. HTTP errors use `{code,message,data:null,request_id}` and the same request ID is returned in `X-Request-ID`.
- Retryable mutations are idempotent: duplicate application, confirmation, notification, upload completion, account request, and maintenance operations return the existing state or a domain conflict instead of duplicating records.
- `409` means a valid request conflicts with current state. `403` means the authenticated actor lacks the required active grant.

## Endpoint matrix

| Area | Endpoints | Authorization and behavior |
| --- | --- | --- |
| Health | `GET /health`, `GET /ready` | Public. Liveness and database/config readiness respectively. |
| Auth | `POST /api/auth/send-code`, `/register`, `/login`, `/reset-password` | Public, rate limited. Codes are purpose-bound. Login/register return token and user. |
| Account | `GET/PATCH /api/auth/profile`, `POST /verify-email`, `/logout`, `/change-password`, `/deactivate`, `GET/POST /account-requests` | Authenticated. Password/reset/deactivation revoke active sessions. Account requests are user-scoped and paginated. |
| Personal area | `GET /api/me/activities`, `/api/me/groups`, `/api/profiles/{user_id}`, `PATCH /api/me/profile`, `GET/PATCH /api/me/settings` | Authenticated. Collections are deterministic and limited to 40 items per page. Public profiles omit private fields entirely; owners see their own configured fields. Profile edits reuse onboarding validation, while settings updates accept only visibility and notification preferences. |
| Posts | `GET/POST /api/posts`, `GET /api/posts/my`, `GET/PATCH/DELETE /api/posts/{id}`, `POST /close`, `/reopen`, `/archive` | Authenticated reads; verified user creates. Owner, scoped post manager, or operator mutates according to capability. Writes are moderated and audited. |
| Applications | `GET/POST /api/applications`, `GET /my`, `POST /{id}/accept`, `/reject`, `/withdraw` | Authenticated and paginated. Applicant withdraws before team confirmation; post manager decides. Capacity/deadline/state are rechecked transactionally. |
| Messages | `GET /api/messages/conversations`, `GET /api/messages/{conversation_id}`, `POST /send`, `/confirm-team`, `/close` | Conversation participant only. Lists are paginated. Blocks/restrictions are enforced server-side. Contact unlock occurs only after bilateral confirmation. |
| Teams | `GET /api/teams/my`, `GET /api/teams/{id}`, task/member/owner/archive mutations below `/api/teams/{id}` | Team member reads; owner or member capability controls writes. Tasks support create, edit, reorder, complete, delete. Contacts are member-only. |
| Topics/tags | Authenticated reads under `/api/topics`, `/api/tags`, and `/api/search`; writes under the same topic/tag prefixes | Official organization role or scoped topic grant controls writes. Tag proposals enter operator review and cannot directly become canonical tags. |
| Scoped responsibility | Topic/post collaborator list, invite, accept, and revoke paths | Authenticated, paginated lists. Manager/owner invites; target accepts; expiry/revocation is checked on every protected write. |
| Organizations | Application, renewal, invitation, member, and ownership-transfer endpoints under `/api/organizations` | Campus-verified users apply. Evidence upload ownership and private status are validated. Organization owner manages members; target accepts invitations/transfers. Lists are paginated. |
| Organization review | `GET /api/operators/organization-applications`, `GET /{id}`, `POST /{id}/review` | Operator only; private evidence appears only in authorized detail/reviewer URL. |
| Platform roles | `GET /api/operators/roles`, `GET /roles/my`, role invite/accept/suspend/revoke paths | User sees own invitations. Operators see queue; senior operator mutates. Acceptance requires password reauthentication. Last senior operator is protected. |
| AI | `POST /api/agent/post-draft`, `/classify-review`, `/match`, `/team-plan` | Authenticated. Input is moderated before Coze, output is schema-validated, unauthorized IDs are rejected, and deterministic fallback is available. Coze receives no contact, evidence, password, token, or unrestricted user data. |
| Moderation | Report/block/appeal endpoints under `/api/moderation`; case/restriction queues under `/api/moderation/operator` | Authenticated user owns reports, blocks, and appeals. Operator queues are paginated and private. Resolution, restrictions, and appeals are audited and notified. |
| Notifications | `GET /api/notifications`, `/unread-count`, `POST /read-all`, `POST /{id}/read` | Authenticated and user-scoped. List is bounded to 40 items per page; writes are idempotent and return the current unread count. |
| Uploads | `POST /api/uploads`, `POST /{id}/complete`, `POST /{id}/attach`, `GET /{id}/review-url` | Authenticated. MIME, suffix, size, object metadata, prefix, owner, target permission, and public/private purpose are enforced. Reviewer URL is operator-only and short-lived. |
| Operations | `GET /api/operators/audit-logs`, `/metrics` | Operator only, paginated where applicable. Sensitive values are recursively redacted. |

## Upload sequence

1. Create an upload ticket with purpose, filename, MIME type, and exact size.
2. `PUT` the file to the returned presigned URL with the returned headers.
3. Complete the upload; the backend verifies object metadata and returns `upload:<id>`.
4. Use `upload:<id>` as organization evidence, or call `/attach` for avatar/topic cover. Topic covers require `target_id` and active topic edit permission.

## AI side effects

- Drafting and classification do not publish content.
- Matching returns only IDs from the backend-supplied candidate set.
- Team planning persists validated task/role data only for an authorized team member and is idempotent under retry.
- Any Coze timeout, malformed output, unknown ID, or unsafe content switches to a controlled backend result and records a metric.

## Conversational Publish (Phase Five)

- `GET /api/publish/context?kind=casual_invitation|topic_team&topic_id=` requires an active, verified account. Returns linked activity metadata, participation mode, allowed purposes and derived join modes, inherited standard tags, field defaults, maximum capacity and an opaque `revision`. Missing/hidden activities cannot be used.
- `POST /api/agent/post-draft` accepts optional `purpose` and `publish_context_revision`. With the new contract, a stale revision returns HTTP 409; a forbidden purpose returns 403. The server corrects model-supplied activity identity, required fields, next question and completion. Unknown/skipped required values do not count as complete; explicitly no required role does. The legacy workflow payload is unchanged.
- Recruitment requires activity, total people including the author, roles (or explicit none), schedule and location; linked recruitment additionally requires a deadline. Official signup requires activity, capacity, deadline and instructions. Discussion requires activity and text only. User text is still moderated before processing and before persistence.
- `POST /api/posts` accepts `client_request_id` (16-64 ASCII letters/digits/hyphens), `publish_context_revision` and optional `cover_upload_id`. The request key is unique per author; a repeated accepted request returns the original post without another post, upload attachment or notification. Reuse the same key after uncertain network failure; use a fresh key only for a genuinely new draft. A key reused with modified content does not edit the existing post.
- Linked tags are merged server-side during create/update and cannot be removed. User-selected plus inherited tags may not exceed eight; AI suggestions only fill remaining slots. Purpose derives joining behavior through the existing participation policy, including the single official-signup-post restriction.
- `post_cover` upload tickets support JPEG/PNG/WebP, at most 10 MiB. Complete the existing upload protocol, then submit the raw upload ID on Post creation. Only a completed, public, author-owned cover can attach, and one upload cannot attach to two posts. Raw public URLs are not accepted. `OBJECT_STORAGE_PUBLIC_BASE_URL` must use HTTPS; storage and browser CORS must be configured. An optional cover can be removed if upload is unavailable.
- Official signup capacity is bounded to 10,000 (context can impose a lower bound); recruitment remains at most 100. Post success notification is committed atomically with first creation. The database migration `20260913_17` adds the author/request uniqueness guard and supports existing as well as freshly bootstrapped databases.

## Production Verification

Repository tests cannot prove a Neon restore or deployed Render smoke test. Complete the restore rehearsal in `docs/operations/backend-runbook.md`, then verify `/health`, `/ready`, email delivery, object storage, and workflows 1-4 against production-like services before frontend release sign-off.
