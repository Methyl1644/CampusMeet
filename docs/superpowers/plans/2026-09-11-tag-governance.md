# Tag Governance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand the controlled Tag catalog and add an operator-reviewed path for genuinely new concepts proposed by users or Coze.

**Architecture:** Keep canonical Tags and aliases as the only values accepted on posts and topics. Add a proposal queue for unknown reusable concepts; AI and users may submit candidates, while only operators can approve, merge, or reject them.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2, PostgreSQL/SQLite, pytest

**Spec:** `docs/superpowers/specs/2026-09-11-tag-governance-and-resource-permissions-design.md`

## Global Constraints

- AI can propose concepts but cannot activate or merge Tags.
- Existing Tag IDs remain stable.
- Exact event names, time, place, member count, and organizations do not become Tags.
- All review decisions are audited.

---

### Task 1: Expand and correct the controlled catalog

**Files:**
- Create: `src/services/content_catalog.py`
- Modify: `src/services/content.py`
- Test: `tests/test_tag_governance.py`

**Interfaces:**
- Produces: `STANDARD_TAGS: tuple[tuple[str, str, str, str, int, tuple[str, ...]], ...]`
- Produces: `AMBIGUOUS_ALIASES: frozenset[str]`
- Consumes: existing `seed_content_catalog(session)` and `tag_suggestions(session, query)`

- [ ] Write tests proving the catalog contains the activity, skill, role, level, and audience categories and that ambiguous `打球` does not map to basketball.
- [ ] Run `python -m pytest tests/test_tag_governance.py -q` and observe the expected failures.
- [ ] Move the catalog to `content_catalog.py`, expand common campus concepts, and deactivate ambiguous legacy aliases during seeding.
- [ ] Run the focused tests and `tests/test_content_domain.py` until green.

### Task 2: Add the Tag proposal lifecycle

**Files:**
- Modify: `src/storage/database/models/content.py`
- Modify: `src/storage/database/models/__init__.py`
- Create: `src/services/tag_governance.py`
- Modify: `src/api/content.py`
- Test: `tests/test_tag_governance.py`

**Interfaces:**
- Produces: `submit_tag_proposal(session, user, name, category, source_text, suggested_tag_id=None)`
- Produces: `review_tag_proposal(session, reviewer, proposal, decision, target_tag_id=None, canonical_name=None, reason='')`
- API: `POST /api/tags/proposals`, `GET /api/tags/proposals`, `POST /api/tags/proposals/{id}/review`

- [ ] Add failing tests for duplicate proposal counting, existing-alias rejection, operator-only review, approval, merge, rejection, and audit records.
- [ ] Run focused tests and confirm each failure is caused by the missing lifecycle.
- [ ] Add `TagProposal` with a unique normalized name, review metadata, occurrence count, and foreign keys.
- [ ] Implement validation, deduplication, approval/merge/reject transitions, and audit writes.
- [ ] Expose authenticated proposal and operator review routes with bounded fields.
- [ ] Run the focused tests until green.

### Task 3: Carry safe unknown concepts through the AI boundary

**Files:**
- Modify: `src/tools/ai_tools.py`
- Modify: `src/api/agent.py`
- Test: `tests/test_d_ai_fallback.py`
- Test: `tests/test_tag_governance.py`

**Interfaces:**
- Coze output may contain `unknown_concepts: [{name, category, reason}]`.
- Backend response includes sanitized `tag_proposals` with pending proposal IDs.

- [ ] Add failing tests proving candidate Tag IDs outside the backend list are discarded and unknown concepts become pending proposals rather than active Tags.
- [ ] Run the focused tests and observe the expected failures.
- [ ] Validate the optional unknown-concept schema, length, category, and count.
- [ ] Use the title and description when selecting candidate Tags and raise the candidate cap enough to cover the curated catalog.
- [ ] Store sanitized unknown concepts through `submit_tag_proposal` and return proposal references.
- [ ] Run Tag, AI fallback, and content-domain tests until green.

### Task 4: Verify and commit Tag governance

**Files:**
- Modify: `docs/api-alignment.md` if present

- [ ] Document the proposal and review endpoints and Coze `unknown_concepts` field.
- [ ] Run `python -m pytest -q`.
- [ ] Run `git diff --check` and inspect the diff for credentials and unrelated changes.
- [ ] Commit the independently deployable Tag governance feature.

