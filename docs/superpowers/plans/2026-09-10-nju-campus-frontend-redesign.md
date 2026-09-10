# CampusMate NJU Campus Frontend Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the generic CampusMate frontend styling with a responsive 南京大学 campus publication visual system and purposeful motion while preserving every existing route, API contract, permission rule, and content flow.

**Architecture:** Establish a centralized Tailwind/CSS design system, add small reusable motion and campus-brand components, then migrate pages from shared shell inward. Keep API and page state in their existing modules; animation only wraps rendered state and never owns business data.

**Tech Stack:** React 18, TypeScript, Vite 5, Tailwind CSS 3, Motion for React, Lucide React, Fontsource Noto Sans SC, Fontsource Noto Serif SC, Node test runner, Playwright for browser verification.

**Spec:** `docs/superpowers/specs/2026-09-10-nju-campus-frontend-redesign.md`

## Global Constraints

- Preserve all existing URL paths, API request/response fields, authentication checks, topic hierarchy, controlled tags, and Coze fallback behavior.
- Use `#5B2A86` as the primary brand purple, `#175C4A` for verification/safety, `#B17A24` for attention, and warm neutral surfaces.
- Use locally bundled Noto Serif SC for headings and Noto Sans SC for body/interface text.
- Use one 8px card radius system; familiar icon actions continue using `lucide-react`.
- Motion intensity is 5/10 and every transform animation must become immediate under `prefers-reduced-motion: reduce`.
- Do not introduce decorative gradient orbs, marketing hero sections, nested cards, hand-drawn SVG icons, or changed business copy.

---

### Task 1: Design Tokens, Fonts, and Motion Foundation

**Files:**
- Create: `apps/web/src/design/theme-contract.test.ts`
- Create: `apps/web/src/components/motion/Reveal.tsx`
- Modify: `apps/web/package.json`
- Modify: `apps/web/package-lock.json`
- Modify: `apps/web/tailwind.config.js`
- Modify: `apps/web/src/main.tsx`
- Modify: `apps/web/src/index.css`

**Interfaces:**
- Produces: `Reveal({ children, className?, delay?, as? })` for page/list entry animation and shared CSS classes `surface-panel`, `section-label`, `tag-chip`, `icon-button`.

- [ ] **Step 1: Write the failing design contract test**

Create a Node test that reads `index.css` and `tailwind.config.js` and asserts presence of `#5B2A86`, `#175C4A`, both Noto font family names, an 8px card radius, focus-visible styling, and a `prefers-reduced-motion` block.

- [ ] **Step 2: Verify the contract fails**

Run: `node --test --experimental-strip-types src/design/theme-contract.test.ts`

Expected: FAIL because the current palette is blue, fonts are system defaults, and reduced-motion styling is absent.

- [ ] **Step 3: Install and implement the foundation**

Run: `npm install motion @fontsource/noto-sans-sc @fontsource/noto-serif-sc`

Import selected font weights in `main.tsx`. Map `primary-*` to the new purple scale, add semantic campus colors, and replace generic component classes in `index.css`. Implement `Reveal` with `motion/react`, a small upward entrance, bounded delays, and `useReducedMotion()`.

- [ ] **Step 4: Verify the foundation**

Run: `node --test --experimental-strip-types src/design/theme-contract.test.ts`

Expected: PASS.

Run: `npm run build`

Expected: TypeScript and Vite production build succeed.

### Task 2: Shared Campus Shell and Feedback Components

**Files:**
- Create: `apps/web/src/components/CampusMark.tsx`
- Modify: `apps/web/src/layouts/MainLayout.tsx`
- Modify: `apps/web/src/components/Navbar.tsx`
- Modify: `apps/web/src/components/Toast.tsx`
- Modify: `apps/web/src/components/Loading.tsx`
- Modify: `apps/web/src/components/EmptyState.tsx`
- Modify: `apps/web/src/components/SourceBadge.tsx`
- Modify: `apps/web/src/components/StatusBadge.tsx`
- Modify: `apps/web/src/components/RiskTag.tsx`

**Interfaces:**
- Consumes: Task 1 typography, colors, utility classes, and `Reveal`.
- Produces: `CampusMark({ compact?: boolean })` and the responsive desktop/mobile shell used by every authenticated page.

- [ ] **Step 1: Extend the design contract test**

Assert that `Navbar.tsx` renders the campus asset, includes `aria-label` on logout, keeps all five route labels, and that `MainLayout.tsx` uses a `min-h-dvh` application shell.

- [ ] **Step 2: Verify the new assertions fail**

Run: `node --test --experimental-strip-types src/design/theme-contract.test.ts`

Expected: FAIL on the missing campus mark and dynamic viewport shell.

- [ ] **Step 3: Implement the shared shell**

Create the campus mark from `/campus-clocktower-badge.jpg`, redesign desktop navigation as a single 72px publication header, and redesign mobile navigation with safe-area padding. Update feedback components to use semantic colors, stable dimensions, icon tooltips, and restrained entrances.

- [ ] **Step 4: Verify shell behavior**

Run: `node --test --experimental-strip-types src/design/theme-contract.test.ts`

Expected: PASS.

Run: `npm run lint && npm run build`

Expected: both commands succeed without errors.

### Task 3: Discovery, Search, Topic Cards, and Topic Detail

**Files:**
- Create: `apps/web/src/components/TopicCard.tsx`
- Modify: `apps/web/src/components/DiscoveryHub.tsx`
- Modify: `apps/web/src/components/PostCard.tsx`
- Modify: `apps/web/src/pages/TopicDetail.tsx`

**Interfaces:**
- Consumes: existing `getSearchSuggestions`, `getTopics`, `getPosts`, `toggleTopicFollow`, existing `Topic` and `Post` types, and Task 1 `Reveal`.
- Produces: `TopicCard({ topic, index? })`, with official and organization variants; keeps navigation to `/topics/:id` and `/posts/:id` unchanged.

- [ ] **Step 1: Extend the design contract test**

Assert that the discovery surface contains one search input, all three channel labels, direct-topic suggestions before standard tags, removable selected tags, and imports the new `TopicCard` rather than defining a card inline.

- [ ] **Step 2: Verify discovery assertions fail**

Run: `node --test --experimental-strip-types src/design/theme-contract.test.ts`

Expected: FAIL because `TopicCard.tsx` does not exist and the current discovery layout has the old styling.

- [ ] **Step 3: Implement discovery and topic hierarchy**

Use an editorial page masthead with the campus image, animated channel underline, centered search field, anchored suggestion panel, and removable tag chips. Give topic cards a real image region and stronger hierarchy than compact team invitation cards. Redesign topic detail with an official-document header, source metadata, follow feedback, activity body, and clearly subordinate team-post section.

- [ ] **Step 4: Verify discovery**

Run: `node --test --experimental-strip-types src/design/theme-contract.test.ts`

Expected: PASS.

Run: `npm run lint && npm run build`

Expected: both commands succeed.

### Task 4: Authentication and AI Publishing Surfaces

**Files:**
- Modify: `apps/web/src/pages/Login.tsx`
- Modify: `apps/web/src/pages/Publish.tsx`

**Interfaces:**
- Consumes: existing authentication and post-draft API functions without signature changes, Task 1 motion utilities, and `CampusMark`.
- Produces: animated login/register/verification stages and an animated chat plus structured draft workspace.

- [ ] **Step 1: Extend the design contract test**

Assert that `Login.tsx` uses `CampusMark`, preserves login/register/verify states, includes a registration progress line, and that `Publish.tsx` retains the AI/manual fallback, candidate tag controls, and publish action.

- [ ] **Step 2: Verify the new assertions fail**

Run: `node --test --experimental-strip-types src/design/theme-contract.test.ts`

Expected: FAIL on the missing campus layout and progress presentation.

- [ ] **Step 3: Implement authentication and publishing redesign**

Build a desktop two-column campus identity/login composition that collapses to one column on mobile. Animate stage changes with direction-aware fade/slide and preserve every validation and API handler. Recompose publishing as a conversation workspace with an editorial draft margin, animate new messages and tag changes, and keep manual fallback fully visible.

- [ ] **Step 4: Verify authentication and publishing**

Run: `node --test --experimental-strip-types src/design/theme-contract.test.ts`

Expected: PASS.

Run: `npm run lint && npm run build`

Expected: both commands succeed.

### Task 5: Remaining Workflow Pages

**Files:**
- Modify: `apps/web/src/pages/PostDetail.tsx`
- Modify: `apps/web/src/pages/Messages.tsx`
- Modify: `apps/web/src/pages/TeamDetail.tsx`
- Modify: `apps/web/src/pages/Profile.tsx`
- Modify: `apps/web/src/components/ApplicationModal.tsx`

**Interfaces:**
- Consumes: all existing API methods and stores unchanged, plus shared visual components from Tasks 1 and 2.
- Produces: visually consistent application, message, team, and profile workflows.

- [ ] **Step 1: Extend the design contract test**

Assert that each remaining page uses the shared surface classes or `Reveal`, and that application, confirmation, contact lock, safety notice, task controls, profile tabs, and logout actions remain present.

- [ ] **Step 2: Verify the new assertions fail**

Run: `node --test --experimental-strip-types src/design/theme-contract.test.ts`

Expected: FAIL because the pages still use generic card presentation.

- [ ] **Step 3: Recompose the remaining pages**

Apply the campus publication hierarchy without changing handlers. Use unframed sections for page structure, cards only for repeated records and modal content, stable chat dimensions, explicit safety colors, and consistent button/icon states. Replace raw em-dash fallback text in rendered UI with `暂无`.

- [ ] **Step 4: Verify all remaining workflows**

Run: `node --test --experimental-strip-types src/design/theme-contract.test.ts`

Expected: PASS.

Run: `npm run lint && npm run build`

Expected: both commands succeed.

### Task 6: Browser QA, Responsive Fixes, and Final Verification

**Files:**
- Modify only files already listed when a captured defect requires a correction.
- Create: `work/frontend-qa/desktop-home.png`
- Create: `work/frontend-qa/mobile-home.png`
- Create: `work/frontend-qa/desktop-login.png`
- Create: `work/frontend-qa/mobile-publish.png`

**Interfaces:**
- Consumes: completed frontend and the existing local FastAPI data/API.
- Produces: verified screenshots and a production build.

- [ ] **Step 1: Start the local services**

Run backend on port 3000 and Vite on an available localhost port. Seed preview content only if current content endpoints are empty.

- [ ] **Step 2: Capture one bounded QA pass**

Use Playwright at 1440 x 900 and 390 x 844. Exercise login/demo entry, all three discovery channels, keyword suggestion, selected-tag removal, topic detail, AI publishing, messages, and profile. Capture the four named screenshots and inspect browser console errors.

- [ ] **Step 3: Fix the complete QA defect batch**

Correct all observed overlap, overflow, unreadable contrast, blank assets, unstable controls, and mobile safe-area issues in one edit batch. Do not introduce new features during QA.

- [ ] **Step 4: Confirm once and stop polishing**

Repeat the same desktop/mobile captures once. Verify reduced-motion mode, keyboard focus, no horizontal overflow, and no console errors.

- [ ] **Step 5: Run final automated verification**

Run: `node --test --experimental-strip-types src/design/theme-contract.test.ts src/api/auth-feedback.test.ts`

Expected: all tests pass.

Run: `npm run lint && npm run build`

Expected: lint and production build pass.

