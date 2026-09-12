# Desktop Tutorial Content Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove site-authored explanatory copy from desktop business pages and collect it in an authenticated tutorial page.

**Architecture:** Add a static `Tutorial` route inside the existing authenticated shell. Extend the shared navigation with a desktop-only item, then simplify business-page copy without changing APIs, state, permissions, or user-generated content.

**Tech Stack:** React 18, TypeScript, React Router, Tailwind CSS, Motion, Lucide React, Node test runner, Playwright.

**Spec:** `docs/superpowers/specs/2026-09-10-desktop-tutorial-content-migration.md`

## Global Constraints

- Add `教程` to desktop navigation only; mobile bottom navigation remains five columns.
- Preserve topic, post, AI, message, team, tag, status, count, field-label, button-label, and user data.
- Preserve concise operation-result feedback.
- Remove general explanations, examples, onboarding prose, empty-state instructions, and contextual safety prose from business pages.
- Add no backend state, API, dependency, or mobile-specific redesign.

---

### Task 1: Tutorial Route And Desktop Navigation

**Files:**
- Create: `apps/web/src/pages/Tutorial.tsx`
- Modify: `apps/web/src/components/Navbar.tsx`
- Modify: `apps/web/src/router/index.tsx`
- Test: `apps/web/src/design/theme-contract.test.ts`

**Interfaces:**
- Consumes: authenticated `MainLayout`, `NavLink`, existing campus theme utilities.
- Produces: `/tutorial` route and desktop-only `教程` navigation item.

- [ ] **Step 1: Write failing navigation and route assertions**

Add source-contract assertions that `Tutorial.tsx` exists, the router imports and registers it, desktop navigation includes `BookOpen` and `教程`, and mobile navigation maps only `navItems.filter((item) => !item.desktopOnly)` into `grid-cols-5`.

- [ ] **Step 2: Run the contract test and verify RED**

Run: `node --test --experimental-strip-types src/design/theme-contract.test.ts`

Expected: FAIL because the tutorial module and route do not exist.

- [ ] **Step 3: Implement the static tutorial module**

Create six unframed sections named `注册与校园认证`, `查找话题与活动`, `标准标签与搜索`, `AI 辅助发布组队帖`, `申请、消息与确认组队`, and `联系方式与安全`. Use `Reveal`, existing typography tokens, numbered section markers, dividers, and Lucide icons; do not create nested cards.

- [ ] **Step 4: Connect desktop navigation and route**

Add `{ to: '/tutorial', label: '教程', icon: BookOpen, desktopOnly: true }` after messages. Render all items in the desktop map and filter `desktopOnly` items from the mobile map. Import `Tutorial` in the router and add `{ path: 'tutorial', element: <Tutorial /> }`.

- [ ] **Step 5: Run contract and TypeScript checks**

Run: `node --test --experimental-strip-types src/design/theme-contract.test.ts`

Run: `node node_modules/typescript/bin/tsc -b --pretty false`

Expected: both PASS.

### Task 2: Business Page Copy Migration

**Files:**
- Modify: `apps/web/src/components/DiscoveryHub.tsx`
- Modify: `apps/web/src/components/EmptyState.tsx`
- Modify: `apps/web/src/pages/Login.tsx`
- Modify: `apps/web/src/pages/Publish.tsx`
- Modify: `apps/web/src/pages/PostDetail.tsx`
- Modify: `apps/web/src/components/ApplicationModal.tsx`
- Modify: `apps/web/src/pages/Messages.tsx`
- Modify: `apps/web/src/pages/TeamDetail.tsx`
- Modify: `apps/web/src/pages/Profile.tsx`
- Modify: `apps/web/src/pages/TopicDetail.tsx`
- Test: `apps/web/src/design/theme-contract.test.ts`

**Interfaces:**
- Consumes: the tutorial content introduced by Task 1.
- Produces: action-focused business pages with unchanged behavior and data rendering.

- [ ] **Step 1: Add representative copy-removal assertions**

Assert that business sources no longer contain the discovery onboarding sentence, login slogan/helper text, publishing examples, chat safety paragraph, locked-contact explanation, or empty-state action descriptions. Assert those concepts appear in `Tutorial.tsx`.

- [ ] **Step 2: Run the contract test and verify RED**

Run: `node --test --experimental-strip-types src/design/theme-contract.test.ts`

Expected: FAIL on the existing explanatory strings.

- [ ] **Step 3: Simplify discovery and authentication copy**

Remove discovery intro paragraphs and channel subtitles. Reduce the search placeholder to `搜索`. Remove login hero slogan/body, stage descriptions, field helper parentheses, demo explanation, verification guidance, and footer prose while preserving headings, labels, buttons, registration progress, validation, and authentication handlers.

- [ ] **Step 4: Simplify publishing and workflow copy**

Remove publishing examples, AI behavior explanations, draft instructions, contextual safety prose, empty-state instructions, and contact-unlock explanations. Keep generated AI replies, real content, field labels, status text, button labels, and concise toasts.

- [ ] **Step 5: Run contracts and TypeScript checks**

Run: `node --test --experimental-strip-types src/design/theme-contract.test.ts src/api/auth-feedback.test.ts`

Run: `node node_modules/typescript/bin/tsc -b --pretty false`

Expected: all tests and TypeScript PASS.

### Task 3: Desktop Browser QA And Production Verification

**Files:**
- Modify: `work/frontend-qa/run.cjs`
- Create: `work/frontend-qa/desktop-tutorial.png`
- Refresh: `work/frontend-qa/desktop-login.png`
- Refresh: `work/frontend-qa/desktop-home.png`
- Refresh: `work/frontend-qa/desktop-publish.png`

**Interfaces:**
- Consumes: completed tutorial route and simplified desktop pages.
- Produces: browser evidence and a production build.

- [ ] **Step 1: Extend browser checks**

Visit `/tutorial` at 1440 x 900, assert all six sections render, and capture `desktop-tutorial.png`. Continue checking login, home search, topic details, publishing, messages, and profile for console errors and horizontal overflow.

- [ ] **Step 2: Run desktop browser QA**

Run the Playwright script against the existing local Vite server.

Expected: no page errors, console errors, or horizontal overflow.

- [ ] **Step 3: Inspect screenshots once**

Inspect tutorial, login, home, and publish screenshots. Correct only observed overlap, navigation fit, hierarchy, or unreadable content defects.

- [ ] **Step 4: Run final verification**

Run: `node --test --experimental-strip-types src/design/theme-contract.test.ts src/api/auth-feedback.test.ts`

Run: `node node_modules/typescript/bin/tsc -b --pretty false`

Run: `node node_modules/vite/bin/vite.js build`

Expected: tests, TypeScript, and production build PASS.
