# CampusMate Home And Navigation Phase Two Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the approved Meetup-inspired application shell and a personalized, responsive CampusMate home page backed by one resilient aggregate API.

**Architecture:** Add a read-only `/api/home` endpoint whose service composes existing users, followed topics, teams, tasks, conversations, and notifications into stable sections. The React home page consumes this contract through focused navigation and home components; sections own their loading, empty, and degraded states so one missing section does not blank the page.

**Tech Stack:** FastAPI, SQLAlchemy 2, Pydantic/OpenAPI, Pytest, React 18, TypeScript, React Router, Tailwind CSS, Motion, Lucide, Vitest, Testing Library.

**Spec:** `docs/superpowers/specs/2026-09-12-meetup-inspired-product-redesign-design.md`

## Global Constraints

- Keep the logo provisional and do not introduce final brand artwork.
- Keep the existing `/publish` page source and behavior unchanged.
- Use Chinese navigation and product copy.
- Desktop navigation order is logo, 首页, 探索, 发布, flexible space, 消息, 通知, 教程, avatar menu.
- Mobile navigation is 首页, 探索, 发布, 消息, 我的; notifications and tutorial remain reachable from 我的.
- Page background is cool near-white; purple is reserved for selection, links, progress, and primary actions.
- Cards use at most `8px` radius except event cover media, which may use up to `12px`.
- Motion must honor `prefers-reduced-motion`.
- Home API section failures return remaining sections plus section warnings; authentication failure still fails the request.
- No new recommendation AI service; ranking is deterministic and explainable.

---

### Task 1: Home Aggregate Service And API Contract

**Files:**
- Create: `src/services/home.py`
- Create: `src/api/home.py`
- Modify: `src/main.py`
- Modify: `packages/shared/src/types.ts`
- Modify: `packages/shared/src/constants.ts`
- Test: `tests/test_home_feed.py`

**Interfaces:**
- Consumes: existing `User`, `Topic`, `TopicTag`, `TopicFollow`, `Team`, `TeamMember`, `Post`, `Conversation`, `Message`, and `Notification` models.
- Produces: `build_home_feed(session: Session, user: User, now: datetime | None = None) -> dict[str, Any]` and authenticated `GET /api/home`.
- Response keys: `profile`, `deadline_reminder`, `recommended_topics`, `followed_topics`, `joined_groups`, `group_timeline`, `unread`, and `warnings`.

- [ ] **Step 1: Write failing service and API tests**

```python
def test_home_feed_prioritizes_interest_matches_and_future_deadlines(session, user):
    user.interests = ["人工智能"]
    matched = make_topic(session, title="AI 校赛", deadline=utc_days(3), tags=["activity_ai"])
    make_topic(session, title="普通讲座", deadline=utc_days(2), tags=["activity_lecture"])
    feed = build_home_feed(session, user, now=UTC_NOW)
    assert feed["recommended_topics"][0]["id"] == str(matched.id)
    assert feed["recommended_topics"][0]["recommendation_reason"] == "与你的人工智能兴趣相关"

def test_home_feed_returns_followed_topics_joined_groups_badges_and_timeline(session, user):
    seed_follow_team_message_and_notification(session, user)
    feed = build_home_feed(session, user, now=UTC_NOW)
    assert len(feed["followed_topics"]) == 1
    assert len(feed["joined_groups"]) == 1
    assert feed["group_timeline"][0]["team_id"] == feed["joined_groups"][0]["id"]
    assert feed["unread"] == {"messages": 1, "notifications": 1}

def test_home_endpoint_requires_auth_and_wraps_contract(client, auth_headers):
    assert client.get("/api/home").status_code == 401
    response = client.get("/api/home", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["code"] == 0
    assert "recommended_topics" in response.json()["data"]
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `pytest tests/test_home_feed.py -q`

Expected: FAIL because `services.home` and `/api/home` do not exist.

- [ ] **Step 3: Implement deterministic aggregate builders**

```python
SECTION_DEFAULTS = {
    "deadline_reminder": None,
    "recommended_topics": [],
    "followed_topics": [],
    "joined_groups": [],
    "group_timeline": [],
    "unread": {"messages": 0, "notifications": 0},
}

def build_home_feed(session: Session, user: User, now: datetime | None = None) -> dict[str, Any]:
    current = ensure_utc(now or datetime.now(timezone.utc))
    result = {"profile": profile_summary(user), **deepcopy(SECTION_DEFAULTS), "warnings": []}
    for name, builder in HOME_SECTION_BUILDERS.items():
        try:
            result[name] = builder(session, user, current)
        except Exception:
            logger.exception("home section failed", extra={"section": name, "user_id": user.id})
            result["warnings"].append(name)
    return result
```

Implement ranking as: interest-tag overlap descending, future event/deadline before undated content, nearest future date ascending, `updated_at` descending, `id` descending. Include at most eight recommendations, four followed topics, four joined groups, and twelve timeline items. A reminder is the nearest future followed-topic registration deadline within fourteen days.

- [ ] **Step 4: Add the authenticated router and register it**

```python
router = APIRouter(prefix="/home", tags=["home"])

@router.get("")
def home_feed(user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    session = get_session()
    try:
        user = session.get(User, int(user_id))
        if user is None:
            raise HTTPException(status_code=401, detail="登录状态已失效")
        return api_ok(build_home_feed(session, user))
    finally:
        session.close()
```

- [ ] **Step 5: Run focused and contract tests**

Run: `pytest tests/test_home_feed.py tests/test_openapi_snapshot.py -q`

Expected: home tests PASS; OpenAPI snapshot FAIL until Task 6 exports the intentional contract.

- [ ] **Step 6: Commit**

```bash
git add src/services/home.py src/api/home.py src/main.py packages/shared/src/types.ts packages/shared/src/constants.ts tests/test_home_feed.py
git commit -m "feat: add personalized home feed api"
```

---

### Task 2: Frontend Home Data Boundary

**Files:**
- Create: `apps/web/src/api/home.ts`
- Create: `apps/web/src/api/home.test.ts`
- Create: `apps/web/src/features/home/HomeFeedContext.tsx`
- Create: `apps/web/src/features/home/HomeFeedContext.test.tsx`
- Modify: `apps/web/vitest.config.ts`

**Interfaces:**
- Consumes: `API_PATHS.home.feed` and shared `HomeFeed` types from Task 1.
- Produces: `getHomeFeed(): Promise<HomeFeed>`, `homeSectionState(feed, section)`, `HomeFeedProvider`, and `useHomeFeed()` for one shared request across the shell and home page.

- [ ] **Step 1: Write failing API adapter tests**

```ts
it('requests the aggregate home endpoint', async () => {
  mockedGet.mockResolvedValue(feedFixture)
  await expect(getHomeFeed()).resolves.toEqual(feedFixture)
  expect(mockedGet).toHaveBeenCalledWith('/api/home')
})

it('marks only named warning sections as degraded', () => {
  expect(homeSectionState({ ...feedFixture, warnings: ['group_timeline'] }, 'group_timeline')).toBe('degraded')
  expect(homeSectionState(feedFixture, 'recommended_topics')).toBe('ready')
})

it('shares one request between navigation and home consumers', async () => {
  render(
    <HomeFeedProvider>
      <FeedConsumer name="navigation" />
      <FeedConsumer name="home" />
    </HomeFeedProvider>,
  )
  expect(await screen.findByText('navigation:ready')).toBeVisible()
  expect(screen.getByText('home:ready')).toBeVisible()
  expect(mockedGetHomeFeed).toHaveBeenCalledTimes(1)
})
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `node node_modules/vitest/vitest.mjs --run src/api/home.test.ts src/features/home/HomeFeedContext.test.tsx`

Expected: FAIL because `api/home.ts` does not exist.

- [ ] **Step 3: Implement the typed adapter and warning helper**

```ts
export function getHomeFeed() {
  return get<HomeFeed>(API_PATHS.home.feed)
}

export function homeSectionState(feed: HomeFeed, section: HomeWarningSection) {
  return feed.warnings.includes(section) ? 'degraded' : 'ready'
}
```

The provider exposes `{ feed, loading, error, reload }`, starts one request on mount, ignores late results after unmount, and retains the last successful feed while a manual reload is in progress.

- [ ] **Step 4: Run the focused test**

Run: `node node_modules/vitest/vitest.mjs --run src/api/home.test.ts src/features/home/HomeFeedContext.test.tsx`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/api/home.ts apps/web/src/api/home.test.ts apps/web/src/features/home apps/web/vitest.config.ts
git commit -m "feat: add typed home feed client"
```

---

### Task 3: Responsive Application Navigation

**Files:**
- Create: `apps/web/src/components/navigation/UserMenu.tsx`
- Create: `apps/web/src/components/navigation/DesktopHeader.tsx`
- Create: `apps/web/src/components/navigation/MobileNavigation.tsx`
- Modify: `apps/web/src/components/Navbar.tsx`
- Modify: `apps/web/src/layouts/MainLayout.tsx`
- Test: `apps/web/src/components/navigation/Navbar.test.tsx`

**Interfaces:**
- Consumes: authenticated `User`, `useHomeFeed().feed?.unread`, route location, and store logout.
- Produces: `Navbar({ unread, onRefreshHome? })`, keyboard-accessible avatar menu, and fixed mobile bottom navigation.

- [ ] **Step 1: Write failing navigation behavior tests**

```tsx
it('renders the approved desktop order and unread labels', async () => {
  renderNavigation({ messages: 2, notifications: 3 })
  expect(screen.getAllByRole('link').map(link => link.textContent)).toEqual(expect.arrayContaining(['首页', '探索', '发布']))
  expect(screen.getByLabelText('消息，2 条未读')).toBeInTheDocument()
  expect(screen.getByLabelText('通知，3 条未读')).toBeInTheDocument()
})

it('opens and closes the avatar menu with keyboard focus restoration', async () => {
  const trigger = renderNavigation().getByRole('button', { name: '打开个人菜单' })
  await user.click(trigger)
  expect(screen.getByRole('menuitem', { name: '我的活动' })).toBeVisible()
  await user.keyboard('{Escape}')
  expect(trigger).toHaveFocus()
})

it('keeps the mobile navigation to five items', () => {
  renderNavigation()
  expect(screen.getByLabelText('移动端主导航').querySelectorAll('a')).toHaveLength(5)
})
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `node node_modules/vitest/vitest.mjs --run src/components/navigation/Navbar.test.tsx`

Expected: FAIL because the new components and menu behavior do not exist.

- [ ] **Step 3: Build the desktop header and avatar menu**

Use Lucide `MessageCircle`, `Bell`, `CircleHelp`, `ChevronDown`, `CalendarDays`, `UsersRound`, `UserRound`, `Settings`, and `LogOut`. Use icon-only buttons with tooltips and accessible names. Close on outside click, `Escape`, route change, and menu-item activation; restore focus to the trigger.

- [ ] **Step 4: Build the mobile navigation and shell spacing**

Use exactly 首页, 探索, 发布, 消息, 我的. The publish action has the visual emphasis; the other four use familiar icons. Maintain stable `64px` navigation height plus safe-area padding.

- [ ] **Step 5: Run navigation tests and TypeScript**

Run: `node node_modules/vitest/vitest.mjs --run src/components/navigation/Navbar.test.tsx`

Run: `node node_modules/typescript/bin/tsc -b`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/components/navigation apps/web/src/components/Navbar.tsx apps/web/src/layouts/MainLayout.tsx apps/web/src/components/navigation/Navbar.test.tsx
git commit -m "feat: rebuild responsive application navigation"
```

---

### Task 4: Home Summary Rail And Deadline Reminder

**Files:**
- Create: `apps/web/src/components/home/ProfileSummary.tsx`
- Create: `apps/web/src/components/home/MyEventsSummary.tsx`
- Create: `apps/web/src/components/home/MyGroupsSummary.tsx`
- Create: `apps/web/src/components/home/DeadlineReminder.tsx`
- Create: `apps/web/src/components/home/HomeSidebar.test.tsx`

**Interfaces:**
- Consumes: `HomeProfile`, `HomeTopicCard[]`, `HomeGroupCard[]`, and `DeadlineReminder | null`.
- Produces: a desktop summary rail, compact mobile summary row, controlled 参加中/已收藏 tabs, and dismissible deadline reminder.

- [ ] **Step 1: Write failing component tests**

```tsx
it('switches between attending and saved event summaries without layout shift', async () => {
  render(<MyEventsSummary attending={attending} saved={saved} />)
  await user.click(screen.getByRole('tab', { name: '已收藏' }))
  expect(screen.getByText(saved[0].title)).toBeVisible()
  expect(screen.getByRole('link', { name: '查看全部活动' })).toHaveAttribute('href', '/profile?tab=events')
})

it('omits a missing reminder and lets users dismiss an existing one', async () => {
  const { rerender } = render(<DeadlineReminder reminder={null} />)
  expect(screen.queryByRole('status')).not.toBeInTheDocument()
  rerender(<DeadlineReminder reminder={reminder} />)
  await user.click(screen.getByRole('button', { name: '关闭截止提醒' }))
  expect(screen.queryByRole('status')).not.toBeInTheDocument()
})
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `node node_modules/vitest/vitest.mjs --run src/components/home/HomeSidebar.test.tsx`

Expected: FAIL because home summary components do not exist.

- [ ] **Step 3: Implement the profile, events, and groups summaries**

Show one recent item per tab on desktop and a compact horizontal item on mobile. Empty states use direct actions to `/discover?view=events` and `/discover?view=groups`. Use unframed profile summary plus two individual `8px` cards; do not nest cards.

- [ ] **Step 4: Implement the reminder**

The banner shows deadline label, remaining-day copy, event title, and “查看活动”. Store dismissal in component state only so a fresh session may show a still-relevant reminder again.

- [ ] **Step 5: Run focused tests**

Run: `node node_modules/vitest/vitest.mjs --run src/components/home/HomeSidebar.test.tsx`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/components/home
git commit -m "feat: add home summaries and deadline reminder"
```

---

### Task 5: Recommendation Rail, Group Timeline, And Home Page States

**Files:**
- Create: `apps/web/src/components/home/HomeEventCard.tsx`
- Create: `apps/web/src/components/home/RecommendationRail.tsx`
- Create: `apps/web/src/components/home/GroupTimeline.tsx`
- Create: `apps/web/src/components/home/HomeSkeleton.tsx`
- Modify: `apps/web/src/pages/Home.tsx`
- Test: `apps/web/src/pages/Home.test.tsx`

**Interfaces:**
- Consumes: `useHomeFeed()`, all home section components from Tasks 3-4, and `HomeFeed.warnings`.
- Produces: complete desktop two-column and mobile one-column home experience.

- [ ] **Step 1: Write failing page tests for success, empty, partial, and retry states**

```tsx
it('renders personalized recommendations and joined-group timeline', async () => {
  mockedGetHomeFeed.mockResolvedValue(feedFixture)
  renderHome()
  expect(await screen.findByRole('heading', { name: '为你推荐' })).toBeVisible()
  expect(screen.getByText(feedFixture.recommended_topics[0].title)).toBeVisible()
  expect(screen.getByRole('heading', { name: '来自我的小组' })).toBeVisible()
})

it('keeps healthy sections visible when one section is degraded', async () => {
  mockedGetHomeFeed.mockResolvedValue({ ...feedFixture, group_timeline: [], warnings: ['group_timeline'] })
  renderHome()
  expect(await screen.findByText(feedFixture.recommended_topics[0].title)).toBeVisible()
  expect(screen.getByText('小组动态暂时无法加载')).toBeVisible()
})

it('offers a retry after the aggregate request fails', async () => {
  mockedGetHomeFeed.mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce(feedFixture)
  renderHome()
  await user.click(await screen.findByRole('button', { name: '重新加载首页' }))
  expect(await screen.findByText(feedFixture.profile.nickname)).toBeVisible()
})
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `node node_modules/vitest/vitest.mjs --run src/pages/Home.test.tsx`

Expected: FAIL because Home still renders `DiscoveryHub`.

- [ ] **Step 3: Implement the event card and horizontal rail**

Card scan order is cover, title, date/deadline, organizer, participation/follower count, recommendation reason. Use fixed aspect ratio and stable card width; the horizontal list uses native scrolling plus arrow controls on desktop. The card itself is a link; the favorite affordance is displayed as state in this phase and becomes interactive in Phase 3.

- [ ] **Step 4: Implement group timeline and empty/degraded states**

Group tasks are grouped by calendar date. Each row links to `/teams/:id`, shows team name, task title, due time, and completion status. Empty state links to group exploration; degraded state is explicit and does not replace recommendations.

- [ ] **Step 5: Replace Home with the complete page orchestration**

Read the single shared request from `useHomeFeed()` and call its `reload()` on demand. While loading, reserve stable geometry with skeletons. `MainLayout` wraps both `Navbar` and `Outlet` in `HomeFeedProvider`, so navigation badges and the page always read the same feed without a global server-cache dependency.

- [ ] **Step 6: Run focused tests, full frontend tests, and build**

Run: `node node_modules/vitest/vitest.mjs --run src/pages/Home.test.tsx`

Run: `node node_modules/vitest/vitest.mjs --run`

Run: `node node_modules/typescript/bin/tsc -b && node node_modules/vite/bin/vite.js build`

Expected: PASS; Vite may retain the existing chunk-size advisory only.

- [ ] **Step 7: Commit**

```bash
git add apps/web/src/components/home apps/web/src/pages/Home.tsx apps/web/src/pages/Home.test.tsx
git commit -m "feat: build personalized meetup-style home"
```

---

### Task 6: Contract Export, Regression, And Visual Verification

**Files:**
- Modify: `docs/api/openapi.json`
- Modify only if verification finds a defect: files from Tasks 1-5
- Test: `tests/test_home_feed.py`
- Test: `apps/web/src/pages/Home.test.tsx`

**Interfaces:**
- Consumes: completed Phase 2 implementation.
- Produces: committed OpenAPI contract and evidence that desktop, tablet, mobile, reduced-motion, keyboard, and production-build states work.

- [ ] **Step 1: Export the intentional OpenAPI change**

Run: `python scripts/export_openapi.py`

Expected: `docs/api/openapi.json` contains `GET /api/home` and no unrelated contract churn.

- [ ] **Step 2: Run the full automated suites**

Run: `pytest -q`

Run: `node node_modules/vitest/vitest.mjs --run`

Run: `node node_modules/typescript/bin/tsc -b && node node_modules/vite/bin/vite.js build`

Run: `git diff --check`

Expected: all commands exit `0`; only existing dependency deprecation and Vite chunk-size advisories are acceptable.

- [ ] **Step 3: Start local API and web previews**

Run: `python -m uvicorn main:app --host 127.0.0.1 --port 3000`

Run: `node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5175`

Expected: API health and `/home` load locally.

- [ ] **Step 4: Verify three viewports and reduced motion**

Use Playwright at `1440x900`, `1024x768`, and `390x844`. Confirm: no horizontal overflow; header/menu do not overlap; desktop rail and mobile single-column layout are correct; cards retain dimensions while loading; user menu is keyboard operable; recommendation rail works; reduced-motion disables translations.

- [ ] **Step 5: Commit final verification fixes and contract**

```bash
git add docs/api/openapi.json apps/web/src src tests packages/shared/src
git commit -m "test: verify home shell phase two"
```
