# Management Center Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a permission-aware management center for platform roles, organization review and membership, and activity collaborators.

**Architecture:** Add one typed frontend API module and one routed management page composed from focused section components. Reuse existing backend mutations and add only a current-user organization summary endpoint needed by the UI.

**Tech Stack:** React 18, TypeScript, React Router, Axios, Tailwind CSS, Vitest, FastAPI, SQLAlchemy, Pytest

**Spec:** `docs/superpowers/specs/2026-09-14-management-center-design.md`

## Global Constraints

- Preserve `AUTH_ACCESS_MODE=allowlist`; management roles never replace login allowlisting.
- Backend authorization remains authoritative for every action.
- Follow existing CampusMate design tokens and Lucide icon patterns.
- Do not add dependencies or database tables.
- Keep ordinary publishing and team participation unchanged.

---

### Task 1: Current-User Management Context

**Files:**
- Modify: `src/api/identity.py`
- Modify: `src/services/identity.py`
- Test: `tests/test_identity_projection.py`

**Interfaces:**
- Produces: `GET /api/organizations/my-managed` returning active organizations where the current user is owner, with `organization_id`, `organization_name`, `role`, and `expires_at`.

- [x] Write a failing backend test proving owners see active organizations and publishers do not.
- [x] Run `pytest tests/test_identity_projection.py -q` and verify the new test fails with a missing route/service function.
- [x] Add a focused identity service projection and authenticated API route.
- [x] Run `pytest tests/test_identity_projection.py -q` and verify it passes.

### Task 2: Typed Management API Client

**Files:**
- Create: `apps/web/src/api/management.ts`
- Modify: `packages/shared/src/constants.ts`
- Modify: `packages/shared/src/types.ts`
- Test: `apps/web/src/api/management.test.ts`
- Modify: `apps/web/vitest.config.ts`

**Interfaces:**
- Produces: `getManagementPermissions`, `getPlatformRoles`, `invitePlatformRole`, `suspendPlatformRole`, `revokePlatformRole`, `getOrganizationApplications`, `reviewOrganizationApplication`, `getManagedOrganizations`, `getOrganizationMembers`, `inviteOrganizationMember`, `revokeOrganizationMember`, `transferOrganizationOwnership`, `getTopicCollaborators`, `inviteTopicCollaborator`, and `revokeTopicCollaborator`.

- [x] Write failing client tests asserting exact method, URL, and body contracts.
- [x] Run the management API test and verify imports fail because the module does not exist.
- [x] Add shared management types, paths, and the API module using existing client helpers.
- [x] Run the management API test and verify all request-contract tests pass.

### Task 3: Permission-Aware Route And Menu

**Files:**
- Create: `apps/web/src/features/management/managementAccess.ts`
- Create: `apps/web/src/pages/Management.test.tsx`
- Create: `apps/web/src/pages/Management.tsx`
- Modify: `apps/web/src/router/index.tsx`
- Modify: `apps/web/src/components/navigation/UserMenu.tsx`
- Modify: `apps/web/src/components/navigation/Navbar.test.tsx`

**Interfaces:**
- Consumes: `getManagementPermissions()` and management identity types.
- Produces: `/management`, `deriveManagementSections(context)`, and conditional `管理中心` menu entry.

- [x] Write failing tests for authorized section derivation, no-access state, and conditional user-menu entry.
- [x] Run the page and navigation tests and verify they fail for the missing route and menu item.
- [x] Implement permission loading, route registration, access derivation, and the conditional menu link.
- [x] Run the tests and verify authorized users see only permitted sections.

### Task 4: Platform And Organization Operations

**Files:**
- Create: `apps/web/src/features/management/PlatformRolesPanel.tsx`
- Create: `apps/web/src/features/management/OrganizationReviewsPanel.tsx`
- Create: `apps/web/src/features/management/OrganizationMembersPanel.tsx`
- Modify: `apps/web/src/pages/Management.test.tsx`

**Interfaces:**
- Consumes: typed management API functions from Task 2.
- Produces: accessible tables and forms for role invitations, organization decisions, member invitations/removal, and ownership transfer.

- [x] Add focused interaction coverage for authorized platform mutations and API error contracts.
- [x] Run the page test and verify the controls are absent.
- [x] Implement compact panels with loading, empty, form-preserving error, and confirmation states.
- [x] Run the page and API tests and verify mutations refresh their own data and surface backend errors.

### Task 5: Activity Collaborator Operations

**Files:**
- Create: `apps/web/src/features/management/TopicCollaboratorsPanel.tsx`
- Modify: `apps/web/src/pages/Management.test.tsx`

**Interfaces:**
- Consumes: collaborator API functions from Task 2.
- Produces: activity lookup plus coordinator/editor/manager invitation and revocation controls.

- [x] Add collaborator request-contract and access-scope tests.
- [x] Run the page test and verify the collaborator workflow is missing.
- [x] Implement the activity collaborator panel with role descriptions and inline confirmation.
- [x] Run the management tests and verify the workflow contracts pass.

### Task 6: Verification And Delivery

**Files:**
- Modify only files required by verification findings.

**Interfaces:**
- Produces: deployable branch containing the management center and the preceding allowlist compatibility fix.

- [x] Run focused backend identity, platform-role, permission, and collaboration tests.
- [x] Run focused frontend management, navigation, and affected post-detail tests.
- [x] Run TypeScript checking and `vite build`.
- [x] Run `git diff --check` and inspect the final diff for unrelated changes.
- [x] Commit all intended changes with clear messages and push the current feature branch to `origin`.
