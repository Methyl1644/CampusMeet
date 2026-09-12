# CampusMate Official Identity and Responsible Accounts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let an ordinary campus-verified account become a verified organization representative, official publisher, event/topic responsible person, or post collaborator through explicit evidence, invitation, acceptance, expiry, revocation, and audit workflows.

**Architecture:** Keep identity and authorization separate. Campus verification proves the person belongs to the university; organization verification proves an organization and its initial owner; platform roles are global internal roles; topic and post roles are scoped grants. Public badges are computed from currently active records and never from user-editable profile fields or AI output.

**Tech Stack:** FastAPI, SQLAlchemy, PostgreSQL/SQLite, Pydantic, Alembic, React/TypeScript, pytest.

**Spec:** `docs/superpowers/specs/2026-09-09-auth-prototype-design.md` and `docs/superpowers/specs/2026-09-11-tag-governance-and-resource-permissions-design.md`.

## Global Constraints

- A campus email alone does not prove that a user represents the university, an organization, or an event.
- AI may extract an organization name or suggest a duplicate; it cannot approve identity, grant a role, or publish an official activity.
- Platform operator, organization member, topic collaborator, and post collaborator are different scopes.
- Every grant requires an identified grantor, an acceptance step where applicable, an effective time, an expiry or review policy, and an audit record.
- Organization evidence is private. Public API responses expose only status, organization identity, role, scope, and validity period.
- No account may grant a role broader than the role it currently holds.
- Official badges disappear immediately when verification expires, membership is revoked, or the scoped grant ends.

## Role Model

| Layer | Roles | Scope | Granted by |
| --- | --- | --- | --- |
| Platform | operator, senior_operator | Entire platform | Bootstrap or senior operator |
| Organization | owner, publisher, member | One verified organization | Platform approval for first owner; active owner thereafter |
| Activity/topic | manager, editor, coordinator | One topic/event | Operator, organization owner, or active topic manager |
| Recruitment post | editor, application_manager | One post | Post author or operator |

## Task 1: Complete the Verification Data Model and Migrations

**Files:**
- Create: `src/storage/database/models/identity.py`
- Modify: `src/storage/database/models/content.py`
- Modify: `src/storage/database/models/__init__.py`
- Create: `migrations/versions/20260911_02_identity_governance.py`
- Create: `tests/test_identity_models.py`

- [x] Add structured organization application fields for school scope, official page, responsible-person statement, evidence reference, review reason, and expiry.
- [x] Add organization invitation state with inviter, invitee, requested role, token or authenticated acceptance, expiry, accepted time, and revoked time.
- [x] Add platform role grants instead of relying only on a mutable `users.site_role` value; preserve `site_role` during migration for compatibility.
- [x] Add ownership-transfer records so an organization can replace its responsible person without deleting history.
- [x] Add unique constraints preventing multiple active applications, owners, or duplicate invitations for the same scope where policy requires uniqueness.
- [x] Verify empty-database and current-production-schema upgrades with migration tests.

## Task 2: Complete Organization Application and Operator Review

**Files:**
- Modify: `src/api/content.py`
- Create: `src/api/identity.py`
- Create: `src/services/identity.py`
- Create: `src/api/schemas/identity.py`
- Create: `tests/test_organization_verification.py`

- [x] Replace raw request dictionaries with Pydantic application and review schemas.
- [x] Add `GET /api/organizations/applications/my` so applicants can see pending, approved, rejected, expired, and renewal states.
- [x] Add a paginated operator queue and application detail endpoint; only operators can read private evidence.
- [x] Require a review reason for rejection and record all review transitions in `AuditLog`.
- [x] On approval, create or reuse the verified organization and grant the applicant the initial active `owner` role.
- [x] Return a derived identity summary in `/api/auth/profile` rather than changing a user-editable field.
- [x] Add renewal and resubmission paths without overwriting prior applications.

## Task 3: Replace Direct Organization Role Changes with Invitations

**Files:**
- Modify: `src/api/content.py`
- Modify: `src/services/permissions.py`
- Modify: `src/services/identity.py`
- Create: `tests/test_organization_invitations.py`

- [x] Change organization member creation from immediate `active` assignment to a pending invitation.
- [x] Add invite-list, accept, decline, revoke, and member-list endpoints.
- [x] Require the invited account to be campus verified and to accept while the invitation is valid.
- [x] Allow active owners to invite `publisher` or `member`; do not allow an owner to create another owner directly.
- [x] Prevent the last active owner from being revoked before ownership is transferred.
- [x] Verify expired organizations and memberships cannot create organization activities or grant roles.

## Task 4: Govern Platform Official Accounts

**Files:**
- Modify: `src/services/content.py`
- Modify: `src/services/permissions.py`
- Create: `src/api/operators.py`
- Create: `tests/test_platform_roles.py`

- [x] Keep `BOOTSTRAP_OPERATOR_EMAIL` only for establishing the first operator.
- [x] Add senior-operator-only endpoints to invite, activate, suspend, and revoke additional operators.
- [x] Require explicit acceptance and recent reauthentication before an operator role becomes active.
- [x] Prevent self-promotion, self-review, and removal of the last senior operator.
- [x] Audit every operator action and expose no operator-management endpoint to normal organization owners.

## Task 5: Bind Responsible People to Specific Activities and Posts

**Files:**
- Modify: `src/api/permissions.py`
- Modify: `src/services/permissions.py`
- Modify: `src/api/content.py`
- Modify: `src/api/posts.py`
- Create: `tests/test_responsible_account_scopes.py`

- [x] Preserve topic roles already defined as `coordinator`, `editor`, and `manager`, including invite, accept, expiry, and revoke behavior.
- [x] Require an official topic to be created by an operator or imported into an operator review queue before publication.
- [x] Require an organization topic to reference the creator's active verified organization and publisher/owner membership.
- [x] Allow a normal campus account to become responsible for one event only through a scoped topic invitation; do not elevate the account globally.
- [x] Preserve post roles `application_manager` and `editor`, allowing a normal user to help operate only the specified recruitment post.
- [ ] Add transfer and replacement operations that leave historical grants in place for auditing.

## Task 6: Return Trust Badges and Permission Summaries Safely

**Files:**
- Modify: `src/api/auth.py`
- Modify: `src/api/content.py`
- Modify: `src/api/permissions.py`
- Modify: `packages/shared/src/types.ts`
- Create: `tests/test_identity_projection.py`

- [x] Add a derived profile identity summary containing campus verification, active organization roles, active topic roles, active post roles, and expiry dates.
- [x] Return public topic responsible-person badges only when the grant and its parent organization/topic are active.
- [x] Distinguish `平台官方收录`, `认证组织发布`, `活动负责人`, and `帖子协作者` in API data.
- [x] Never expose private evidence, reviewer notes, personal contact details, or internal operator scope in public topic/post responses.
- [ ] Remove frontend reliance on `auth_status === "organization"` as the sole source of an organization badge.

## Task 7: Build the Required User and Operator Interfaces

**Files:**
- Create: `apps/web/src/api/identity.ts`
- Modify: `apps/web/src/pages/Profile.tsx`
- Modify: `apps/web/src/pages/TopicDetail.tsx`
- Modify: `apps/web/src/pages/PostDetail.tsx`
- Create: `apps/web/src/pages/IdentityCenter.tsx`
- Create: `apps/web/src/pages/OperatorIdentityReview.tsx`
- Modify: `apps/web/src/router.tsx`

- [ ] Add organization application, status, rejection-reason, renewal, and evidence-management views.
- [ ] Add pending invitation acceptance/decline and owner member-management views.
- [ ] Add topic/post collaborator management only for users with the corresponding capability.
- [ ] Add a quiet operator review queue with evidence detail, duplicate organization warning, approval/rejection, expiry, and audit history.
- [ ] Show scoped badges beside the relevant organization, activity, or post rather than as a misleading global account badge.

## Task 8: Release Verification

**Files:**
- Create: `tests/test_identity_governance_e2e.py`
- Modify: `docs/e2e-checklist.md`
- Modify: `docs/deployment/render-neon.md`

- [ ] Test campus user application, operator approval, initial owner activation, publisher invitation and acceptance, organization-topic publication, topic-manager invitation, post-manager invitation, expiry, revocation, ownership transfer, and renewal.
- [ ] Test all privilege-escalation attempts, including forged organization IDs, self-grants, expired grants, and AI-produced role names.
- [ ] Run the complete backend and frontend suites.
- [ ] Deploy migrations before application code, then verify the identity summary and permission checks against production data.

## Recommended Delivery Order

1. Tasks 1-3: finish organization verification and invitation integrity.
2. Task 4: secure platform official accounts.
3. Tasks 5-6: complete scoped event/post responsibility and public trust badges.
4. Tasks 7-8: expose the workflows and verify production behavior.
