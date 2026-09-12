# CampusMate Personal Area Phase Four Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the user-owned area with My Activities, My Groups, notifications, public profile, settings, tutorial, footer, and a responsive integration of the existing messaging workflow.

**Architecture:** Add bounded read models for personal collections and public profiles while keeping the current auth, notification, conversation, application, and team services authoritative. React receives dedicated routes for each user task; the existing `/profile?...` links remain compatibility redirects so Phase 2 navigation continues to work.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic, Pydantic/OpenAPI, Pytest, React 18, TypeScript, React Router, Tailwind CSS, Motion, Lucide, Vitest, Testing Library, Playwright.

**Spec:** `docs/superpowers/specs/2026-09-12-meetup-inspired-product-redesign-design.md`

## Global Constraints

- Preserve the Phase 2 navigation and Phase 3 activity/group contracts.
- Keep the logo provisional and keep the Publish page unchanged.
- Contacts are private by default and are never exposed by the public-profile endpoint unless the owner explicitly enables the existing contact visibility field.
- My Activities has exactly `参加中`, `已收藏`, and `已结束`; My Groups has exactly `已加入`, `申请中`, `已收藏`, and `已归档`.
- Collection endpoints use deterministic pagination and `page_size <= 40`; notification/message pages use bounded initial loads and explicit pagination.
- Notification read and read-all operations are idempotent and update navigation unread state without a full reload.
- Desktop messages use conversation list plus detail; mobile uses separate list and conversation screens.
- Existing contact-exchange/team-confirmation permissions remain unchanged.
- Settings edits reuse onboarding normalization and validation; unsaved input survives a request failure.
- Tutorial content is task based and deep-linkable by stable section identifiers.
- The footer contains CampusMate contact information and the existing repository URL only; do not invent social accounts.
- All routes have loading, empty, degraded, retry, and unauthorized behavior where applicable.
- Motion honors `prefers-reduced-motion`; no page content may be covered by desktop or mobile navigation.

---

### Task 1: Personal Collection And Public Profile APIs

**Files:**
- Create: `src/services/personal_area.py`
- Create: `src/api/personal.py`
- Create: `src/api/schemas/personal.py`
- Modify: `src/main.py`
- Modify: `src/api/auth.py`
- Test: `tests/test_phase_four_personal_area.py`

**Interfaces:**
- Produces `GET /api/me/activities?view=attending|saved|past&page=&page_size=`.
- Produces `GET /api/me/groups?view=joined|pending|saved|archived&page=&page_size=`.
- Produces `GET /api/profiles/{user_id}` with privacy-filtered profile fields and bounded public activity/group previews.
- Produces `PATCH /api/me/profile` by reusing onboarding field normalizers and explicit visibility controls.

- [ ] Write failing tests for every collection view, deterministic ordering, duplicates across TeamMember paths, privacy, missing users, owner visibility, pagination bounds, and invalid profile updates.
- [ ] Run `pytest tests/test_phase_four_personal_area.py -q` and confirm missing-route failures.
- [ ] Implement batch projections using Phase 3 card summaries; do not duplicate card serialization logic.
- [ ] Derive past activity from the effective activity end/start/deadline timestamp and archived groups from Team/Post lifecycle state.
- [ ] Apply privacy at serialization time and ensure hidden fields never appear as `null` keys that reveal configuration.
- [ ] Run focused tests plus onboarding/auth regressions.
- [ ] Commit as `feat: add personal collection APIs`.

---

### Task 2: Settings Preferences And Notification Semantics

**Files:**
- Create: `migrations/versions/20260913_15_user_notification_preferences.py`
- Modify: `src/storage/database/models/user.py`
- Modify: `src/api/auth.py`
- Modify: `src/api/notifications.py`
- Modify: `src/services/onboarding.py`
- Test: `tests/test_phase_four_settings_notifications.py`
- Test: `tests/test_migrations.py`

**Interfaces:**
- Produces bounded `User.notification_preferences` JSON with boolean keys for applications, teams, moderation, deadlines, and messages.
- Produces `GET /api/me/settings` and `PATCH /api/me/settings` for profile visibility and notification preferences.
- Existing notification list/read/read-all routes remain compatible and return current unread count in mutation results.

- [ ] Write failing migration/API tests for defaults, normalization, unknown-key rejection, payload byte bounds, read idempotency, read-all idempotency, pagination, and unread-count updates.
- [ ] Run focused tests and verify expected failures.
- [ ] Add the migration after Phase 3 revision `20260913_14`; sanitize old preference JSON before checks.
- [ ] Centralize preference normalization and use it in onboarding/profile/settings write paths.
- [ ] Extend notification mutations without changing existing event creation semantics.
- [ ] Run migration upgrade/downgrade/upgrade, focused tests, and auth/notification regressions.
- [ ] Commit as `feat: add privacy and notification settings`.

---

### Task 3: Typed Personal Client And Route Compatibility

**Files:**
- Modify: `packages/shared/src/types.ts`
- Modify: `packages/shared/src/constants.ts`
- Create: `apps/web/src/api/personal.ts`
- Create: `apps/web/src/api/notifications.ts`
- Modify: `apps/web/src/router/index.tsx`
- Create: `apps/web/src/pages/ProfileRedirect.tsx`
- Test: `apps/web/src/api/personal.test.ts`
- Test: `apps/web/src/router/index.test.tsx`

**Interfaces:**
- Produces typed collection, public profile, settings, notification page, and unread mutation contracts.
- Produces canonical routes `/my/activities`, `/my/groups`, `/notifications`, `/users/:id`, and `/settings`.
- Compatibility mapping: `/profile?tab=events` -> `/my/activities`, `tab=groups` -> `/my/groups`, `view=notifications` -> `/notifications`, `view=settings` -> `/settings`, and `view=public` or bare `/profile` -> the signed-in user public page.

- [ ] Write failing API/route tests for all compatibility links, query preservation, invalid views, auth guards, and typed request transport.
- [ ] Run focused tests and verify missing client/routes.
- [ ] Add types/API paths and one explicit compatibility redirect component.
- [ ] Update Phase 2 menu/home links to canonical destinations while keeping redirects tested.
- [ ] Run focused tests, navigation tests, and TypeScript compilation.
- [ ] Commit as `feat: add personal area routes and client`.

---

### Task 4: My Activities, My Groups, And Notifications Pages

**Files:**
- Create: `apps/web/src/pages/MyActivities.tsx`
- Create: `apps/web/src/pages/MyGroups.tsx`
- Create: `apps/web/src/pages/Notifications.tsx`
- Create: `apps/web/src/components/personal/CollectionTabs.tsx`
- Create: `apps/web/src/components/personal/CollectionPage.tsx`
- Create: `apps/web/src/components/personal/NotificationItem.tsx`
- Test: `apps/web/src/pages/MyActivities.test.tsx`
- Test: `apps/web/src/pages/MyGroups.test.tsx`
- Test: `apps/web/src/pages/Notifications.test.tsx`

**Interfaces:**
- Consumes Task 3 clients and Phase 3 cards.
- Notification targets route only through an allowlisted target-type mapper; unknown targets render as text without unsafe links.

- [ ] Write failing tests for all tabs, URL state, loading/empty/error/retry, pagination, notification read/read-all, unread synchronization, unknown targets, and keyboard navigation.
- [ ] Run focused tests and confirm page modules are absent.
- [ ] Build restrained full-width page bands with reusable tabs and Phase 3 cards; do not nest cards.
- [ ] Implement optimistic notification read state with rollback and update the shared Home feed/unread provider after successful mutations.
- [ ] Add clear empty-state links back to Explore.
- [ ] Run focused tests and configured frontend tests.
- [ ] Commit as `feat: build personal collections and notifications`.

---

### Task 5: Public Profile And Settings Experiences

**Files:**
- Replace: `apps/web/src/pages/Profile.tsx`
- Create: `apps/web/src/pages/PublicProfile.tsx`
- Create: `apps/web/src/pages/Settings.tsx`
- Create: `apps/web/src/components/personal/ProfileHeader.tsx`
- Create: `apps/web/src/components/personal/ProfileSections.tsx`
- Create: `apps/web/src/components/personal/SettingsSection.tsx`
- Test: `apps/web/src/pages/PublicProfile.test.tsx`
- Test: `apps/web/src/pages/Settings.test.tsx`

**Interfaces:**
- Public profile shows only server-projected fields, public activity/group previews, and a signed-in-owner edit action.
- Settings owns profile editing, privacy toggles, notification preferences, password change, and existing account lifecycle actions.

- [ ] Write failing tests for owner/visitor views, every privacy field, empty sections, long content, failed-save draft retention, password errors/success, account actions, and keyboard labels.
- [ ] Run focused tests and confirm old Profile does not satisfy the separation.
- [ ] Build a Meetup-inspired profile hierarchy with an unframed identity header and full-width content sections.
- [ ] Build focused settings sections using toggles for booleans and explicit save/retry feedback; reuse existing avatar upload and auth endpoints.
- [ ] Keep destructive account actions visually separated and preserve their existing confirmation requirements.
- [ ] Run focused tests, auth feedback tests, and TypeScript compilation.
- [ ] Commit as `feat: redesign public profile and settings`.

---

### Task 6: Messages, Tutorial, And Footer Integration

**Files:**
- Modify: `apps/web/src/pages/Messages.tsx`
- Create: `apps/web/src/pages/Conversation.tsx`
- Modify: `apps/web/src/pages/Tutorial.tsx`
- Create: `apps/web/src/components/layout/SiteFooter.tsx`
- Modify: `apps/web/src/layouts/MainLayout.tsx`
- Modify: `apps/web/src/router/index.tsx`
- Test: `apps/web/src/pages/Messages.test.tsx`
- Test: `apps/web/src/pages/Tutorial.test.tsx`
- Test: `apps/web/src/components/layout/SiteFooter.test.tsx`

**Interfaces:**
- Desktop `/messages` retains split-pane operation; mobile `/messages` lists conversations and `/messages/:conversationId` shows one conversation.
- Tutorial section ids are `activity-vs-group`, `find-teammates`, `official-signup`, `discussion`, `applications-and-contact`, and `reporting-and-privacy`.
- Footer consumes repository/contact values from checked-in configuration constants, never from hard-coded fake links.

- [ ] Write failing tests for desktop/mobile message flow, direct conversation route, empty/error/retry, send/confirm/close states, deep-linked tutorial focus, footer destinations, and reduced motion.
- [ ] Run focused tests and verify current single-page message behavior fails mobile expectations.
- [ ] Extract shared conversation components without changing existing contact-unlock rules.
- [ ] Replace tutorial placeholder content with the six approved task sections and links back to relevant product routes.
- [ ] Add the dark, responsive footer after page content with real project contact/repository destinations and no app-store/social placeholders.
- [ ] Run focused tests, message API regressions, and frontend suite.
- [ ] Commit as `feat: integrate messages tutorial and footer`.

---

### Task 7: Contract, End-To-End, And Visual Verification

**Files:**
- Modify: `docs/api/openapi.json`
- Modify: `docs/api/backend-contract.md`
- Create: `.superpowers/sdd/2026-09-13-personal-area-phase-four/qa/personal-area-playwright.cjs`
- Modify only if verification finds a defect: files from Tasks 1-6

**Interfaces:**
- Produces documented Phase 4 contracts and end-to-end evidence from navigation links through each personal task.

- [ ] Export and review OpenAPI; document privacy omission semantics, collection views, settings, and notification mutation counts.
- [ ] Run full Pytest, configured Vitest, TypeScript, Vite build, Alembic upgrade/downgrade/upgrade, and `git diff --check`.
- [ ] Verify My Activities, My Groups, Notifications, public profile, Settings, Messages, Tutorial, and footer at `1440x900`, `1024x768`, and `390x844`.
- [ ] Verify normal/reduced motion, keyboard-only navigation, unread synchronization, deep links, long Chinese text, empty/failure states, and no horizontal overflow or fixed-bar occlusion.
- [ ] Exercise the end-to-end paths: home summary -> collection; notification -> target; menu -> public profile/settings/logout; mobile messages list -> conversation.
- [ ] Stop all disposable services and confirm ports are closed.
- [ ] Commit intentional fixes/docs as `test: verify personal area phase four`.

