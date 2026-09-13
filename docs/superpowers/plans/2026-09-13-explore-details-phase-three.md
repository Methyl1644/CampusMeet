# CampusMate Explore And Details Phase Three Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the approved two-class activity/group Explore experience, rich detail pages, favorites, participation state, and enforceable official-signup rules without redesigning the existing Publish page.

**Architecture:** Extend the existing `Topic -> Post -> Team -> TeamMember` model instead of introducing a second participation system. A participation policy service owns official-signup and join rules, while a read-only Explore service projects stable card/detail contracts for FastAPI and React; the current content/post endpoints remain compatible and gain additive fields and filters.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic, Pydantic/OpenAPI, Pytest, React 18, TypeScript, React Router, Tailwind CSS, Motion, Lucide, Vitest, Testing Library, Playwright.

**Spec:** `docs/superpowers/specs/2026-09-12-meetup-inspired-product-redesign-design.md`

## Global Constraints

- Keep the logo provisional and do not add final brand artwork.
- Do not redesign or restructure `apps/web/src/pages/Publish.tsx` in this phase.
- Explore exposes exactly two Chinese top-level views: `活动` and `组队`; the existing three channels remain backend governance fields.
- `Topic` is the formal activity record; `Post` is the group/discussion entry; participation is derived through `TeamMember -> Team -> Post.topic_id`.
- Participation modes are exactly `open_team`, `official_signup`, and `information_only`.
- Post purposes are exactly `team_recruitment`, `official_signup`, and `discussion`; join modes are exactly `application`, `direct`, and `none`.
- One activity may have at most one effective official-signup post, enforced by both database and service checks.
- Favorites and direct joins are idempotent; repeated requests never create duplicate records.
- Existing `/topics/:id`, `/posts/:id`, `/teams/:id`, content, post, application, and team APIs remain compatible.
- The activity/group search state is independent and restored when switching views or returning to Explore.
- Search remains below the activity/group heading and never moves into the global navigation.
- Cards have stable media geometry and no layout shift; card radius is at most `8px`, while cover media may use up to `12px`.
- Normal motion is `180-240ms`; `prefers-reduced-motion` removes translation and keeps only immediate or short fades.
- All list inputs use explicit page-size caps; all detail previews use bounded counts.
- Use Chinese product copy and cool near-white backgrounds; reserve purple for selection, links, and primary actions.

---

### Task 1: Additive Participation Domain Migration

**Files:**
- Create: `migrations/versions/20260913_14_explore_participation.py`
- Modify: `src/storage/database/models/content.py`
- Modify: `src/storage/database/models/post.py`
- Modify: `src/storage/database/models/__init__.py`
- Test: `tests/test_phase_three_participation.py`
- Test: `tests/test_migrations.py`

**Interfaces:**
- Produces `Topic.location_name: str | None`, `Topic.campus_scope: str | None`, `Topic.capacity: int | None`, and `Topic.participation_mode: str`.
- Produces `Post.cover_url: str | None`, `Post.purpose: str`, and `Post.join_mode: str`.
- Produces `PostBookmark(post_id: int, user_id: int, created_at: datetime)` with unique `(post_id, user_id)` and a user/created index.
- The migration follows current revision `20260913_13` and backfills old topics/posts to `open_team`, `team_recruitment`, and `application`.

- [ ] Write migration/model tests that assert safe defaults, allowed-value checks, positive capacities, bookmark uniqueness, upgrade from the pre-Phase-3 schema, and downgrade reversibility.
- [ ] Run `pytest tests/test_phase_three_participation.py tests/test_migrations.py -q` and confirm failures are caused by missing fields/table/revision.
- [ ] Add model fields, dialect-safe check constraints, `PostBookmark`, indexes, and the additive migration.
- [ ] Sanitize legacy values before installing checks; never delete legacy Topic/Post rows.
- [ ] Add a partial unique index for effective `official_signup` posts with status in `recruiting` or `full`, scoped by `topic_id`, for SQLite and PostgreSQL.
- [ ] Run the focused tests, `alembic upgrade head`, `alembic downgrade 20260913_13`, and `alembic upgrade head` on a disposable test database.
- [ ] Commit as `feat: add explore participation domain`.

---

### Task 2: Central Participation Policy And Team Lifecycle

**Files:**
- Create: `src/services/participation.py`
- Modify: `src/api/posts.py`
- Modify: `src/api/applications.py`
- Modify: `src/api/teams.py`
- Modify: `src/services/content.py`
- Test: `tests/test_phase_three_participation.py`

**Interfaces:**
- Produces `validate_post_participation(session: Session, user: User, payload: Mapping[str, Any], *, existing: Post | None = None) -> ParticipationDecision`.
- Produces `join_post_directly(session: Session, post: Post, user: User) -> TeamMember` with idempotent semantics.
- Produces `get_join_state(session: Session, post: Post, user_id: int) -> Literal['owner','joined','pending','rejected','available','closed']`.
- Consumes existing organization/topic collaborator permissions and existing application/team creation behavior.

- [ ] Write failing policy tests for all nine participation-mode/purpose combinations, organizer authorization, official-signup uniqueness, information-only rejection, application join, direct join, capacity, and repeat requests.
- [ ] Run the focused tests and verify the expected policy failures.
- [ ] Implement immutable enums/constants and one policy decision object; route every Post create/update and application/direct-join path through it.
- [ ] Reuse the existing Team for official signup and create it transactionally on first direct join; lock/check capacity and uniqueness in the same transaction.
- [ ] Return stable domain error codes/messages for forbidden purpose, duplicate official signup, closed content, full capacity, and invalid join mode.
- [ ] Run focused tests plus existing post/application/team suites.
- [ ] Commit as `feat: enforce activity participation rules`.

---

### Task 3: Shared Explore Read Models And Bounded APIs

**Files:**
- Create: `src/services/explore.py`
- Create: `src/api/schemas/explore.py`
- Create: `src/api/explore.py`
- Modify: `src/main.py`
- Modify: `src/api/content.py`
- Modify: `src/api/posts.py`
- Test: `tests/test_phase_three_explore.py`

**Interfaces:**
- Produces authenticated `GET /api/explore/activities` and `GET /api/explore/groups` with `q`, `tag_ids`, date/status/type/campus filters, `page`, and `page_size <= 40`.
- Produces `GET /api/explore/activities/{topic_id}` and `GET /api/explore/groups/{post_id}` detail projections.
- Activity card/detail fields include location/campus/capacity/dates/follower and participant counts, participant preview, participation mode, favorite and participation state, bounded related groups, tags, trust badges, and organizer.
- Group card/detail fields include purpose/join mode/cover, current/target members, bookmark/join state, author, bounded member preview, needed roles, linked activity summary, tags, and status.

- [ ] Write failing API/service tests for both views, combined filters, deterministic pagination, deduplicated participant counts, bounded previews, missing covers, linked content, authentication, and 404s.
- [ ] Run `pytest tests/test_phase_three_explore.py -q` and verify missing-module/route failures.
- [ ] Implement select-based batch projections without per-card queries; cap participant/related previews at eight and list pages at forty.
- [ ] Keep existing `GET /api/content/topics`, `GET /api/posts`, and detail payloads compatible while adding the same new fields where relevant.
- [ ] Give old coverless content stable category placeholder keys, not generated remote URLs.
- [ ] Run focused tests and query-count assertions.
- [ ] Commit as `feat: add bounded explore read APIs`.

---

### Task 4: Favorites, Direct Join, And Related Groups

**Files:**
- Create: `src/api/favorites.py`
- Modify: `src/main.py`
- Modify: `src/api/content.py`
- Modify: `src/api/posts.py`
- Modify: `src/services/explore.py`
- Test: `tests/test_phase_three_favorites.py`

**Interfaces:**
- Keeps existing topic follow endpoint and adds explicit idempotent `PUT /api/favorites/topics/{id}` and `DELETE /api/favorites/topics/{id}` aliases.
- Produces idempotent `PUT /api/favorites/posts/{id}` and `DELETE /api/favorites/posts/{id}`.
- Produces `POST /api/posts/{id}/join` for `join_mode=direct`; application-mode content continues to use the existing application endpoint.
- Produces `GET /api/topics/{id}/related-posts?purpose=&page=&page_size=` with authorization/status filtering and `page_size <= 20`.

- [ ] Write failing tests for repeated favorite/unfavorite/direct-join calls, concurrent uniqueness, missing/hidden content, capacity, related-purpose filtering, and projection state changes.
- [ ] Run the focused tests and verify route/behavior failures.
- [ ] Implement transactional upsert/delete semantics and map database uniqueness races to a successful idempotent result.
- [ ] Emit existing notification/audit events for successful first-time joins; repeat requests must not duplicate notifications.
- [ ] Run focused tests plus notification/application regressions.
- [ ] Commit as `feat: add explore favorites and direct join`.

---

### Task 5: Typed Explore Client And Independent View State

**Files:**
- Modify: `packages/shared/src/types.ts`
- Modify: `packages/shared/src/constants.ts`
- Create: `apps/web/src/api/explore.ts`
- Create: `apps/web/src/features/explore/exploreState.ts`
- Test: `apps/web/src/features/explore/exploreState.test.ts`
- Test: `apps/web/src/api/explore.test.ts`

**Interfaces:**
- Produces TypeScript unions `ParticipationMode`, `PostPurpose`, `JoinMode`, `JoinState`, plus exact activity/group card and detail interfaces matching Task 3.
- Produces `readExploreState(search: URLSearchParams)`, `writeExploreState(view, state)`, and `useExploreState()` that preserve separate activity/group query and filter state in the URL.
- Produces typed client functions for list/detail/favorite/direct-join/related-post requests and supports request cancellation.

- [ ] Write failing unit tests for contract decoding, comma-separated tag transport, independent state restoration, unknown-value normalization, pagination reset on filter change, and aborted-request handling.
- [ ] Run the focused Vitest files and verify missing-interface/module failures.
- [ ] Add shared contracts/API paths and implement a single URL-state codec with safe defaults.
- [ ] Keep legacy Topic/Post interfaces source compatible and layer new projection types beside them.
- [ ] Run focused tests and TypeScript compilation.
- [ ] Commit as `feat: add typed explore client state`.

---

### Task 6: Meetup-Inspired Two-Class Explore Experience

**Files:**
- Replace: `apps/web/src/components/DiscoveryHub.tsx`
- Modify: `apps/web/src/pages/Discover.tsx`
- Create: `apps/web/src/components/explore/ExploreSwitcher.tsx`
- Create: `apps/web/src/components/explore/ExploreFilters.tsx`
- Create: `apps/web/src/components/explore/CategoryRail.tsx`
- Create: `apps/web/src/components/explore/ActivityCard.tsx`
- Create: `apps/web/src/components/explore/GroupCard.tsx`
- Create: `apps/web/src/components/explore/ExploreGrid.tsx`
- Create: `apps/web/src/components/explore/ExploreSkeleton.tsx`
- Test: `apps/web/src/pages/Discover.test.tsx`
- Test: `apps/web/src/components/explore/ExploreCards.test.tsx`

**Interfaces:**
- Consumes Task 5 URL state and typed API.
- Produces exactly two tabs with headings `发现值得认真准备的校园活动` and `找到此刻正缺你的队伍`.
- Activity cards link to `/topics/:id`; group cards link to `/posts/:id`; all favorite buttons are independently keyboard operable.

- [ ] Write failing tests for tab copy/selection, search placement, independent filter restoration, loading/empty/error/retry states, pagination, favorite mutation, stable card metadata, and keyboard labels.
- [ ] Run focused tests and confirm current DiscoveryHub fails the new contract.
- [ ] Implement the segment switcher, heading, search, filter row, horizontal category rail, and responsive result grid in that order.
- [ ] Use fixed media aspect ratios, line clamping, native horizontal scrolling, desktop arrow controls, and optimistic favorites with rollback/error feedback.
- [ ] Animate only selection and result changes for `180-240ms`; replace translations with short fades under reduced motion.
- [ ] Ensure mobile filters use a dialog/sheet with a real close control and focus return.
- [ ] Run focused tests, accessibility assertions, and TypeScript compilation.
- [ ] Commit as `feat: build activity and group explore views`.

---

### Task 7: Activity, Group, And Team Detail Experiences

**Files:**
- Modify: `apps/web/src/pages/TopicDetail.tsx`
- Modify: `apps/web/src/pages/PostDetail.tsx`
- Modify: `apps/web/src/pages/TeamDetail.tsx`
- Create: `apps/web/src/components/details/ActivityHero.tsx`
- Create: `apps/web/src/components/details/ActivityFacts.tsx`
- Create: `apps/web/src/components/details/ParticipantPreview.tsx`
- Create: `apps/web/src/components/details/RelatedGroups.tsx`
- Create: `apps/web/src/components/details/StickyActions.tsx`
- Create: `apps/web/src/components/details/GroupHero.tsx`
- Test: `apps/web/src/pages/TopicDetail.test.tsx`
- Test: `apps/web/src/pages/PostDetail.test.tsx`
- Test: `apps/web/src/pages/TeamDetail.test.tsx`

**Interfaces:**
- Activity action rules: `open_team` shows favorite/share/find teammates and a temporary `/publish?kind=topic_team&topic_id=:id` shortcut; `official_signup` highlights the one official signup; `information_only` shows explanation/discussions only.
- Group action rules: owner, joined, pending, available, full, closed, application, direct, and none each map to one unambiguous action state.
- Desktop uses a sticky bottom action band; mobile uses a safe-area bottom bar without covering page content.

- [ ] Write failing detail tests for each participation mode and join state, favorite/share, related-group purpose labels, bounded participant previews, publish query link, missing cover, long content, and sticky-action accessibility.
- [ ] Run focused tests and verify the old pages fail the new interaction contract.
- [ ] Implement the activity hero/facts/details/location text/participants/related groups hierarchy, keeping maps out of scope.
- [ ] Implement group details with linked activity, purpose badge, capacity, needed roles, organizer, member preview, and application/direct-join actions.
- [ ] Retain existing application modal and team collaboration controls; restyle only their containing detail experience.
- [ ] Add bottom padding equal to sticky bars and verify no overlap at desktop/tablet/mobile widths.
- [ ] Run focused tests and the configured frontend suite.
- [ ] Commit as `feat: redesign activity and group details`.

---

### Task 8: Contract Export, Regression, And Browser Verification

**Files:**
- Modify: `docs/api/openapi.json`
- Modify: `docs/api/backend-contract.md`
- Create: `.superpowers/sdd/2026-09-13-explore-details-phase-three/qa/explore-details-playwright.cjs`
- Modify only if verification finds a defect: files from Tasks 1-7

**Interfaces:**
- Consumes the completed Phase 3 implementation.
- Produces committed API documentation and evidence for desktop, tablet, mobile, reduced-motion, keyboard, empty, loading, failure, and long-content states.

- [ ] Export OpenAPI with `python scripts/export_openapi.py` and review the diff for only intentional additive contract changes.
- [ ] Document participation modes, post purposes, join modes, favorite idempotency, and official-signup errors in `backend-contract.md`.
- [ ] Run `pytest -q`.
- [ ] Run the configured Vitest command from `apps/web`, then `tsc -b` and the Vite production build.
- [ ] Run Alembic upgrade/downgrade/upgrade and `git diff --check`.
- [ ] Start disposable local API and web preview processes on available ports and record them in the QA script output.
- [ ] Verify `/discover`, activity details, group details, and team details at `1440x900`, `1024x768`, and `390x844`, plus reduced-motion and keyboard-only navigation.
- [ ] Assert no horizontal overflow, hidden controls, text overlap, card layout shift, blocked content, or sticky-bar occlusion; check screenshots and nonblank media pixels.
- [ ] Stop all disposable processes, confirm their ports are closed, and retain the QA script/results under the ignored SDD workspace.
- [ ] Commit intentional fixes and docs as `test: verify explore details phase three`.

