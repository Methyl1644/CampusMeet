# Resource Permissions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let verified ordinary users receive limited, expiring authority over exactly one topic or recruitment post.

**Architecture:** Add explicit topic and post collaborator tables with invitation states and role presets. Central permission functions combine platform role, organization ownership, authorship, scoped role, revocation, and expiry; every mutating route calls them.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2, PostgreSQL/SQLite, pytest

**Spec:** `docs/superpowers/specs/2026-09-11-tag-governance-and-resource-permissions-design.md`

## Global Constraints

- Grants are pending until accepted and may expire or be revoked.
- A topic coordinator cannot edit topic information.
- A post application manager cannot edit post content.
- Organization publishers do not automatically edit every organization topic.
- Every grant transition and delegated action is audited.

---

### Task 1: Model scoped collaborators and permission checks

**Files:**
- Modify: `src/storage/database/models/content.py`
- Modify: `src/storage/database/models/__init__.py`
- Create: `src/services/permissions.py`
- Test: `tests/test_resource_permissions.py`

**Interfaces:**
- Produces: `can_manage_topic(session, user, topic, capability) -> bool`
- Produces: `can_manage_post(session, user, post, capability) -> bool`
- Topic capabilities: `moderate_posts`, `edit_topic`, `manage_collaborators`
- Post capabilities: `manage_applications`, `update_status`, `edit_post`

- [ ] Add failing tests for platform operators, organization owners, creators, scoped roles, pending/revoked/expired grants, and publisher isolation.
- [ ] Run focused tests and confirm the expected failures.
- [ ] Add `TopicCollaborator` and `PostCollaborator` models with unique resource/user constraints and lifecycle timestamps.
- [ ] Implement role-to-capability checks and active-state handling in one service.
- [ ] Run focused tests until green.

### Task 2: Add invitation, acceptance, listing, and revocation APIs

**Files:**
- Create: `src/api/permissions.py`
- Modify: `src/main.py`
- Test: `tests/test_resource_permissions.py`

**Interfaces:**
- API: topic and post collaborator list/create, self-accept, and revoke routes.
- Input roles are restricted to the role sets defined by the permission service.

- [ ] Add failing route-level tests for unauthorized grant, pending invitation, self-acceptance, duplicate update, expiry, list, and revoke.
- [ ] Run focused tests and observe failures from the missing routes.
- [ ] Implement routes with verified-user checks, expiry parsing, audit logs, and idempotent updates.
- [ ] Register the router in `main.py`.
- [ ] Run focused tests until green.

### Task 3: Enforce delegated permissions on current operations

**Files:**
- Modify: `src/api/content.py`
- Modify: `src/tools/application_tools.py`
- Modify: `src/api/agent.py`
- Modify: `src/api/posts.py`
- Test: `tests/test_resource_permissions.py`
- Test: `tests/test_team_confirmation.py`

**Interfaces:**
- Topic update consumes `can_manage_topic(..., 'edit_topic')`.
- Application list/accept/reject and teammate matching consume `can_manage_post(..., 'manage_applications')`.
- Post update consumes `can_manage_post(..., 'edit_post')`.

- [ ] Add failing tests for each delegated operation and for the capability boundary between coordinator/editor and application-manager/editor.
- [ ] Run focused tests and observe permission failures.
- [ ] Replace local owner checks with the central permission service.
- [ ] Add bounded post editing and topic-linked post moderation routes with audit records.
- [ ] Run resource, team, content, and agent tests until green.

### Task 4: Verify and commit resource permissions

**Files:**
- Modify: `docs/api-alignment.md` if present

- [ ] Document roles, capabilities, invitation lifecycle, and routes.
- [ ] Run `python -m pytest -q`.
- [ ] Run `git diff --check` and inspect the diff for credentials and unrelated changes.
- [ ] Commit the independently deployable resource-permission feature.
