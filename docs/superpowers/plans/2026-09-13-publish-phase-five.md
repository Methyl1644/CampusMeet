# CampusMate Publish Phase Five Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign Publish into a clear Meetup-inspired creation flow and close the activity-detail-to-tagged-group loop with automatic prefill, inherited tags, purpose selection, and official-signup enforcement.

**Architecture:** Keep one Post creation contract and one moderation pipeline. A server-issued publish context supplies immutable activity metadata, allowed purposes/join modes, inherited tags, and user permissions; both conversational drafting and the structured form consume that context, while the central Phase 3 participation policy remains the final authority.

**Tech Stack:** FastAPI, SQLAlchemy 2, Pydantic/OpenAPI, Pytest, React 18, TypeScript, React Router, Tailwind CSS, Motion, Lucide, Vitest, Testing Library, Playwright.

**Spec:** `docs/superpowers/specs/2026-09-12-meetup-inspired-product-redesign-design.md`

## Global Constraints

- Preserve all moderation, governance, organization, topic collaborator, and audit rules.
- The Phase 3 participation policy is authoritative; the frontend never grants itself official-signup permission.
- Activity detail shortcuts use `/publish?kind=topic_team&topic_id=:id`; casual creation uses `/publish`.
- A linked post inherits all activity tag ids server-side; clients may add standard tags up to the existing total cap but cannot remove inherited tags.
- `open_team` allows `team_recruitment` and `discussion`; `official_signup` allows authorized `official_signup` and general `discussion`; `information_only` allows `discussion` only.
- Official signup uses `join_mode=direct`; team recruitment uses `application`; discussion uses `none`.
- The page shows activity/group language, not the old three governance channels.
- User-authored free text and every structured field continue through the existing moderation pipeline before persistence.
- AI drafting may degrade gracefully; manual structured editing must always remain usable.
- Draft input survives AI, publish, upload, and network failures; retry never duplicates a Post.
- Use the existing cool-white/black/purple visual system, at most `8px` card radius and `12px` cover radius.
- Mobile and desktop expose the same fields and rules; no required control may exist only on hover.
- Normal transitions are `180-240ms` and reduced motion removes translation.

---

### Task 1: Authoritative Publish Context And Inherited Tags

**Files:**
- Create: `src/services/publish_context.py`
- Create: `src/api/publish.py`
- Create: `src/api/schemas/publish.py`
- Modify: `src/main.py`
- Modify: `src/api/posts.py`
- Modify: `src/api/schemas/collaboration.py`
- Test: `tests/test_phase_five_publish_context.py`

**Interfaces:**
- Produces authenticated `GET /api/publish/context?kind=casual_invitation|topic_team&topic_id=`.
- Context fields: kind, linked activity summary, participation mode, allowed purposes, default purpose, derived join mode, inherited tags, optional additional tags, field defaults, and permission explanations.
- Post create accepts `purpose`, `join_mode`, `cover_url`, and `client_request_id`; the server overwrites join mode from purpose and unions inherited tags.

- [ ] Write failing tests for casual defaults, all activity participation modes, organizer permissions, inherited tag immutability, tag cap, stale/hidden topics, invalid purpose/join combinations, and repeated `client_request_id`.
- [ ] Run `pytest tests/test_phase_five_publish_context.py -q` and confirm missing service/route failures.
- [ ] Implement a pure context builder over Phase 3 policy and existing permission helpers.
- [ ] Enforce inherited tags and derived join mode inside Post creation, not only in the request schema.
- [ ] Add an idempotency record or existing audit-backed key scoped to author and creation operation; return the original Post for a repeated completed request.
- [ ] Run focused tests plus Phase 3 participation/post regressions.
- [ ] Commit as `feat: add authoritative publish context`.

---

### Task 2: Context-Aware Conversational Drafting

**Files:**
- Modify: `src/api/schemas/agent.py`
- Modify: `src/api/agent.py`
- Modify: `src/services/content.py`
- Test: `tests/test_phase_five_publish_drafting.py`
- Test: `tests/test_d_ai_fallback.py`

**Interfaces:**
- Draft request consumes `purpose`, `publish_context_revision`, and the existing draft/field state.
- Draft response returns immutable activity fields, inherited tags, editable suggestions, selected purpose/join mode, missing fields, and degradation state.
- Linked activity title/tags/purpose rules come from the database context rather than model output.

- [ ] Write failing tests proving the AI cannot change topic id/title/inherited tags/join mode, purpose-specific required fields differ, unsafe text remains blocked, and fallback remains publishable.
- [ ] Run focused tests and verify the old draft contract fails the new assertions.
- [ ] Build the prompt/tool payload from the authoritative context and discard conflicting model fields before returning.
- [ ] Define required fields: recruitment requires target/roles/commitment/scope/deadline; official signup requires capacity/deadline/instructions; discussion requires title/description only.
- [ ] Keep selected standard-tag suggestions bounded and exclude duplicates of inherited tags.
- [ ] Run focused tests and all current AI fallback/moderation tests.
- [ ] Commit as `feat: make publish drafting context aware`.

---

### Task 3: Typed Publish State Machine And Recovery

**Files:**
- Modify: `packages/shared/src/types.ts`
- Modify: `packages/shared/src/constants.ts`
- Create: `apps/web/src/api/publish.ts`
- Modify: `apps/web/src/api/agent.ts`
- Modify: `apps/web/src/api/posts.ts`
- Create: `apps/web/src/features/publish/publishMachine.ts`
- Test: `apps/web/src/features/publish/publishMachine.test.ts`
- Test: `apps/web/src/api/publish.test.ts`

**Interfaces:**
- Produces states `loading_context`, `editing`, `drafting`, `ready`, `publishing`, `published`, and `failed` with explicit events and recoverable draft data.
- Produces one stable client request id per draft lifecycle and context-aware typed API functions.

- [ ] Write failing tests for context loading, purpose changes, immutable fields, dirty edits, AI failure, upload failure, publish retry, duplicate-click prevention, and successful navigation.
- [ ] Run focused tests and verify the state module is absent.
- [ ] Implement a reducer/state machine with serializable state; isolate side effects in page hooks.
- [ ] Preserve edits across recoverable failures and reset the request id only after a confirmed successful Post.
- [ ] Run focused tests and TypeScript compilation.
- [ ] Commit as `feat: add resilient publish state machine`.

---

### Task 4: Meetup-Inspired Publish Experience

**Files:**
- Replace: `apps/web/src/pages/Publish.tsx`
- Create: `apps/web/src/components/publish/PublishHeader.tsx`
- Create: `apps/web/src/components/publish/ActivityContextBand.tsx`
- Create: `apps/web/src/components/publish/PurposeSelector.tsx`
- Create: `apps/web/src/components/publish/ConversationComposer.tsx`
- Create: `apps/web/src/components/publish/StructuredDraft.tsx`
- Create: `apps/web/src/components/publish/PublishPreview.tsx`
- Create: `apps/web/src/components/publish/PublishActions.tsx`
- Test: `apps/web/src/pages/Publish.test.tsx`
- Test: `apps/web/src/components/publish/PublishControls.test.tsx`

**Interfaces:**
- Consumes Task 3 state machine and server context.
- Provides conversational and manual editing as two explicit modes with one shared draft, not two independent forms.
- Linked activity metadata and inherited tags are visible but non-editable; purpose is a segmented control using only allowed values.

- [ ] Write failing tests for casual/linked entry, all purpose choices, permission explanations, mode switching without data loss, inherited tags, AI/manual completion, publish retry, long content, and keyboard operation.
- [ ] Run focused tests and confirm the old page fails the new hierarchy/contract.
- [ ] Implement a quiet work-focused layout: compact header/context band, primary editor, structured draft/preview, and a stable action area; do not create a marketing hero or nested cards.
- [ ] Use icons for mode/tools, a segmented purpose control, standard inputs, and explicit status feedback; keep explanations contextual and short.
- [ ] On mobile, use one column with an accessible draft/preview switcher and safe-area submit bar.
- [ ] Animate mode/content transitions within `180-240ms`; use fades only under reduced motion.
- [ ] Run focused tests, accessibility assertions, and configured frontend suite.
- [ ] Commit as `feat: redesign context aware publish page`.

---

### Task 5: Post Cover Upload And Completion Notifications

**Files:**
- Modify: `src/services/uploads.py`
- Modify: `src/api/uploads.py`
- Modify: `src/api/schemas/uploads.py`
- Modify: `src/api/posts.py`
- Modify: `apps/web/src/api/uploads.ts`
- Modify: `apps/web/src/components/publish/StructuredDraft.tsx`
- Test: `tests/test_phase_five_publish_uploads.py`
- Test: `apps/web/src/components/publish/PublishControls.test.tsx`

**Interfaces:**
- Adds `post_cover` to the existing upload purpose allowlist with the same ownership/completion lifecycle as topic covers.
- A successful first Post creation emits one publish-success notification with a target link; moderation rejection/hidden outcomes use existing moderation notification semantics.

- [ ] Write failing tests for post-cover MIME/size/ownership, unattached uploads, successful attachment, repeat publish notification deduplication, and frontend upload failure recovery.
- [ ] Run focused tests and verify `post_cover` is currently rejected.
- [ ] Extend the existing upload service instead of adding a second uploader.
- [ ] Attach only completed, author-owned post-cover uploads and retain a local preview while upload retries.
- [ ] Emit completion notification only after transaction success.
- [ ] Run focused tests plus upload/notification regressions.
- [ ] Commit as `feat: add publish covers and completion feedback`.

---

### Task 6: Full Contract And End-To-End Closure

**Files:**
- Modify: `docs/api/openapi.json`
- Modify: `docs/api/backend-contract.md`
- Create: `.superpowers/sdd/2026-09-13-publish-phase-five/qa/publish-playwright.cjs`
- Modify only if verification finds a defect: files from Tasks 1-5

**Interfaces:**
- Produces documented Publish context, purpose rules, inherited-tag semantics, idempotency, cover upload, and error codes.
- Produces end-to-end evidence for activity -> publish -> linked group -> detail and direct casual group creation.

- [ ] Export/review OpenAPI and update the backend contract.
- [ ] Run full Pytest, configured Vitest, TypeScript, Vite build, Alembic upgrade/downgrade/upgrade, and `git diff --check`.
- [ ] Verify casual recruitment, linked recruitment, authorized official signup, discussion, forbidden official signup, AI fallback, manual editing, failed retry, and cover upload paths.
- [ ] Verify `/publish` and linked entry at `1440x900`, `1024x768`, and `390x844`, with normal/reduced motion and keyboard-only operation.
- [ ] Confirm activity details display the newly published linked Post with inherited tags and correct purpose/join behavior.
- [ ] Assert no horizontal overflow, layout shift, overlapping action bars, inaccessible controls, or lost draft input.
- [ ] Stop disposable services and confirm ports are closed.
- [ ] Commit intentional fixes/docs as `test: verify publish phase five`.

