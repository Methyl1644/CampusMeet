# Auth and Onboarding Phase One Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace verification-code login and registration-time profile collection with campus-email registration, password-only login, and a resumable six-step first-login profile flow.

**Architecture:** Extend the existing `User` record with onboarding draft fields and expose a small authenticated onboarding API. Keep registration email verification and session issuance, but create users with an incomplete onboarding state; a frontend route guard sends those users to a focused Meetup-inspired wizard until the completion endpoint validates required fields.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, Alembic, Pytest, React 18, TypeScript, React Router, Zustand, Motion, Tailwind CSS, Vite

**Spec:** `docs/superpowers/specs/2026-09-12-meetup-inspired-product-redesign-design.md`

## Global Constraints

- Registration still requires a six-digit code sent to `@nju.edu.cn` or `@smail.nju.edu.cn`.
- Login accepts campus email and password only; login verification codes are removed from the public contract.
- The wizard has exactly six stages: identity, campus profile, interests, goals, skills/availability, preview.
- Nickname, major, grade, and at least three interests are required before completion.
- Every step persists server-side and can resume after refresh or a new session.
- Existing users with a non-empty nickname, major, and grade are backfilled as complete; other existing users enter the wizard.
- Normal motion uses `180-240ms` transitions; `prefers-reduced-motion` removes translation.
- The existing password reset flow remains unchanged.
- The existing Publish page is not modified in this phase.
- Home, navigation, explore, detail, personal-area, and Publish-page work remain in separate phase plans so each subsystem can be reviewed and deployed independently.

---

### Task 1: Persist Onboarding State

**Files:**
- Create: `migrations/versions/20260912_10_user_onboarding.py`
- Modify: `src/storage/database/models/user.py`
- Modify: `tests/test_migrations.py`
- Test: `tests/test_onboarding_flow.py`

**Interfaces:**
- Produces: `User.onboarding_step: int`, `User.onboarding_completed_at: datetime | None`, `User.bio: str | None`, `User.interests: list`, `User.looking_for: list`, `User.availability: dict`, `User.profile_visibility: dict`.
- Migration revision: `20260912_10`, down revision `20260912_09`.

- [ ] **Step 1: Write failing model and migration tests**

Add assertions that fresh metadata contains all onboarding columns and that an Alembic upgrade creates them:

```python
@pytest.fixture
def factory():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory() as session:
        session.add(User(
            id=1,
            email="student@smail.nju.edu.cn",
            password_hash=hash_password("Password2026"),
            nickname="student",
        ))
        session.commit()
    return session_factory


def test_user_model_exposes_onboarding_defaults():
    user = User(email="new@smail.nju.edu.cn", password_hash="hash", nickname="new")
    assert user.onboarding_step is None or user.onboarding_step == 1
    assert user.onboarding_completed_at is None


def test_auth_onboarding_migration_adds_user_profile_columns(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'onboarding.db'}"
    command.upgrade(_alembic_config(database_url), "head")
    names = {item["name"] for item in inspect(create_engine(database_url)).get_columns("users")}
    assert {
        "onboarding_step", "onboarding_completed_at", "bio", "interests",
        "looking_for", "availability", "profile_visibility",
    } <= names
```

- [ ] **Step 2: Run tests and verify the new assertions fail**

Run: `pytest tests/test_onboarding_flow.py tests/test_migrations.py -q`

Expected: failures mention missing `User.onboarding_step` or missing migrated columns.

- [ ] **Step 3: Add model fields and idempotent migration**

Use JSON defaults that match the frontend contract:

```python
onboarding_step: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
onboarding_completed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
bio: Mapped[str | None] = mapped_column(Text)
interests: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
looking_for: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
availability: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
profile_visibility: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
```

The migration must inspect existing columns before adding them and backfill completion only when `nickname`, `major`, and `grade` are non-empty. Use `{}` and `[]` server defaults during migration so existing rows remain readable.

- [ ] **Step 4: Run focused migration tests**

Run: `pytest tests/test_onboarding_flow.py tests/test_migrations.py -q`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add migrations/versions/20260912_10_user_onboarding.py src/storage/database/models/user.py tests/test_migrations.py tests/test_onboarding_flow.py
git commit -m "feat: persist user onboarding state"
```

### Task 2: Simplify Registration and Login Contracts

**Files:**
- Modify: `src/api/schemas/auth.py`
- Modify: `src/api/auth.py`
- Modify: `src/tools/auth_tools.py`
- Modify: `tests/test_auth_verification_flow.py`
- Modify: `packages/shared/src/types.ts`
- Modify: `apps/web/src/api/auth.ts`

**Interfaces:**
- Consumes: onboarding fields from Task 1.
- Produces: `RegisterRequest { account, code, password }` and `LoginRequest { account, password }` in Python and TypeScript.
- Produces: auth user payload fields `onboarding_step`, `onboarding_completed`, `bio`, `interests`, `looking_for`, `availability`, `profile_visibility`.

- [ ] **Step 1: Replace obsolete login-code tests with password-only contract tests**

Add tests that registration accepts no profile fields, creates an incomplete user, and login refuses a missing password:

```python
def test_registration_defers_profile_collection(monkeypatch, tmp_path):
    db = _fresh_sqlite_database(monkeypatch, tmp_path)
    monkeypatch.setattr(auth_tools, "get_session", db.get_session)
    account = "new@smail.nju.edu.cn"
    code = json.loads(auth_tools.register_auth_send_code.invoke({"account": account, "purpose": "register"}))["code"]
    result = json.loads(auth_tools.register_user.invoke({
        "account": account, "code": code, "password": "Password2026",
    }))
    assert result["success"] is True
    assert result["user"]["onboarding_completed"] is False
    assert result["user"]["nickname"] == "new"


def test_login_requires_password(monkeypatch, tmp_path):
    result = json.loads(auth_tools.login_user.invoke({"account": "new@smail.nju.edu.cn", "password": ""}))
    assert result["success"] is False
    assert result["message"] == "请输入密码"
```

Delete `test_registered_user_can_login_with_a_login_code`; retain password lockout coverage.

- [ ] **Step 2: Run the auth tests and verify failure**

Run: `pytest tests/test_auth_verification_flow.py -q`

Expected: registration requires removed profile arguments or login still advertises code authentication.

- [ ] **Step 3: Implement minimal backend contract**

Change schemas to:

```python
class RegisterRequest(BaseModel):
    account: str = Field(min_length=3, max_length=254)
    code: str = Field(min_length=6, max_length=6)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    account: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)
```

Remove `login` from `SendCodeRequest.purpose`, remove code handling from `login_user`, derive a temporary nickname from the email prefix, and initialize onboarding at step 1. Keep rate limiting and password lockout unchanged.

Extend `_user_to_dict` with:

```python
"onboarding_step": user.onboarding_step,
"onboarding_completed": user.onboarding_completed_at is not None,
"bio": user.bio,
"interests": user.interests or [],
"looking_for": user.looking_for or [],
"availability": user.availability or {},
"profile_visibility": user.profile_visibility or {},
```

- [ ] **Step 4: Align shared frontend types and API calls**

Use required password fields and no login code:

```ts
export interface LoginRequest { account: string; password: string }
export interface RegisterRequest { account: string; code: string; password: string }
```

Remove `'login'` from `VerificationCodePurpose` while retaining `register`, `campus_verify`, and `reset_password`.

- [ ] **Step 5: Run backend tests and frontend type checking**

Run: `pytest tests/test_auth_verification_flow.py tests/test_auth_lifecycle.py -q`

Run: `npm run build --workspace @campusmate/web`

Expected: both commands pass after downstream login page compile errors are temporarily resolved in the same task by using the new request shapes.

- [ ] **Step 6: Commit**

```bash
git add src/api/schemas/auth.py src/api/auth.py src/tools/auth_tools.py tests/test_auth_verification_flow.py packages/shared/src/types.ts apps/web/src/api/auth.ts apps/web/src/pages/Login.tsx
git commit -m "feat: simplify campus authentication"
```

### Task 3: Add Resumable Onboarding API

**Files:**
- Create: `src/services/onboarding.py`
- Modify: `src/api/schemas/auth.py`
- Modify: `src/api/auth.py`
- Modify: `src/tools/auth_tools.py`
- Test: `tests/test_onboarding_flow.py`

**Interfaces:**
- Consumes: user fields from Task 1 and serialized auth payload from Task 2.
- Produces: `GET /auth/onboarding`, `PATCH /auth/onboarding`, `POST /auth/onboarding/complete`.
- Produces service functions `onboarding_to_dict(user)`, `update_onboarding(user, payload)`, and `complete_onboarding(user)`.

- [ ] **Step 1: Write failing service tests**

Cover partial persistence, monotonic step progression, required completion fields, and idempotent completion:

```python
def test_onboarding_draft_persists_each_step(factory):
    with factory() as session:
        user = session.get(User, 1)
        data = update_onboarding(session, user, {
            "step": 3, "nickname": "小紫", "major": "软件工程", "grade": "大二",
            "interests": ["人工智能", "产品设计", "羽毛球"],
        })
        session.commit()
        assert data["onboarding_step"] == 3
        assert user.interests == ["人工智能", "产品设计", "羽毛球"]


def test_onboarding_completion_rejects_missing_required_fields(factory):
    with factory() as session:
        user = session.get(User, 1)
        with pytest.raises(ValueError, match="至少选择三个兴趣"):
            complete_onboarding(session, user)
```

- [ ] **Step 2: Run focused tests and verify failure**

Run: `pytest tests/test_onboarding_flow.py -q`

Expected: import failure for `services.onboarding`.

- [ ] **Step 3: Implement service validation and serialization**

`update_onboarding` accepts only known fields, trims strings, limits lists to 30 items, deduplicates list values while preserving order, and clamps `step` to `1..6`. It must never decrease a stored step during autosave.

`complete_onboarding` requires non-empty nickname, major, grade, and three unique interests, sets `onboarding_step = 6`, and assigns `onboarding_completed_at = utcnow()` only once.

- [ ] **Step 4: Expose authenticated endpoints**

Define requests with optional fields and bounded sizes:

```python
class OnboardingUpdateRequest(BaseModel):
    step: int = Field(ge=1, le=6)
    nickname: str | None = Field(default=None, max_length=40)
    avatar: str | None = Field(default=None, max_length=500)
    major: str | None = Field(default=None, max_length=80)
    grade: str | None = Field(default=None, max_length=40)
    interests: list[str] | None = Field(default=None, max_length=30)
    looking_for: list[str] | None = Field(default=None, max_length=12)
    skills: list[str] | None = Field(default=None, max_length=30)
    availability: dict[str, object] | None = None
    bio: str | None = Field(default=None, max_length=500)
    profile_visibility: dict[str, bool] | None = None
```

All endpoints load the authenticated user with `current_user_id`, return `404` for missing users, return `400` with the exact service validation message, and commit only after validation succeeds.

- [ ] **Step 5: Test API and service behavior**

Run: `pytest tests/test_onboarding_flow.py tests/test_auth_verification_flow.py -q`

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/services/onboarding.py src/api/schemas/auth.py src/api/auth.py src/tools/auth_tools.py tests/test_onboarding_flow.py
git commit -m "feat: add resumable onboarding api"
```

### Task 4: Reduce the Login Page to Login, Registration, and Reset

**Files:**
- Modify: `apps/web/src/pages/Login.tsx`
- Modify: `apps/web/src/api/auth.ts`
- Modify: `packages/shared/src/types.ts`
- Create: `apps/web/src/pages/authFlow.ts`
- Create: `apps/web/src/pages/authFlow.test.ts`
- Modify: `apps/web/package.json`
- Modify: `apps/web/package-lock.json`

**Interfaces:**
- Consumes: Task 2 request and response shapes.
- Produces: `destinationAfterAuth(user: User): '/onboarding' | '/home'`.
- Registration and login both call `setAuth`; navigation uses `destinationAfterAuth`.

- [ ] **Step 1: Add Vitest and write the failing routing test**

Add `vitest` as a dev dependency and a `test` script. Test the pure destination function:

```ts
import { describe, expect, it } from 'vitest'
import { destinationAfterAuth } from './authFlow'

describe('destinationAfterAuth', () => {
  it('sends incomplete users to onboarding', () => {
    expect(destinationAfterAuth({ onboarding_completed: false } as never)).toBe('/onboarding')
  })

  it('sends complete users home', () => {
    expect(destinationAfterAuth({ onboarding_completed: true } as never)).toBe('/home')
  })
})
```

- [ ] **Step 2: Run the test and verify failure**

Run: `npm test --workspace @campusmate/web -- --run`

Expected: failure because `authFlow.ts` does not exist.

- [ ] **Step 3: Implement destination helper and simplify Login UI**

Remove the `profile` step, registration skills state, login code field, and login-code request generation. Preserve the current password reset view and CampusMate split-screen identity.

Registration view contains campus email, verification code, set password, and a primary button labeled `注册并继续`. Login contains campus email, password, `忘记密码？`, and `登录`.

Use:

```ts
export function destinationAfterAuth(user: User) {
  return user.onboarding_completed ? '/home' : '/onboarding'
}
```

After either successful call, update auth state and navigate to that result.

- [ ] **Step 4: Run unit test and production build**

Run: `npm test --workspace @campusmate/web -- --run`

Run: `npm run build --workspace @campusmate/web`

Expected: tests and build pass.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/pages/Login.tsx apps/web/src/pages/authFlow.ts apps/web/src/pages/authFlow.test.ts apps/web/src/api/auth.ts packages/shared/src/types.ts apps/web/package.json apps/web/package-lock.json
git commit -m "feat: simplify login and registration ui"
```

### Task 5: Build the Six-Step Meetup-Inspired Wizard

**Files:**
- Create: `apps/web/src/api/onboarding.ts`
- Create: `apps/web/src/pages/Onboarding.tsx`
- Create: `apps/web/src/components/onboarding/OnboardingShell.tsx`
- Create: `apps/web/src/components/onboarding/ChoiceChips.tsx`
- Create: `apps/web/src/components/onboarding/onboardingState.ts`
- Create: `apps/web/src/components/onboarding/onboardingState.test.ts`
- Modify: `packages/shared/src/types.ts`
- Modify: `apps/web/src/index.css`

**Interfaces:**
- Consumes: Task 3 endpoints.
- Produces: `getOnboarding()`, `saveOnboarding(payload)`, `completeOnboarding()`.
- Produces: `OnboardingDraft`, `OnboardingUpdate`, `canContinue(step, draft)`, and `/onboarding` page component.

- [ ] **Step 1: Write failing wizard-state tests**

```ts
describe('canContinue', () => {
  it('requires nickname on step one', () => {
    expect(canContinue(1, { nickname: '' } as OnboardingDraft)).toBe(false)
  })

  it('requires three unique interests on step three', () => {
    expect(canContinue(3, { interests: ['AI', 'AI', '跑步'] } as OnboardingDraft)).toBe(false)
    expect(canContinue(3, { interests: ['AI', '产品', '跑步'] } as OnboardingDraft)).toBe(true)
  })

  it('allows optional steps five and six', () => {
    expect(canContinue(5, {} as OnboardingDraft)).toBe(true)
    expect(canContinue(6, {} as OnboardingDraft)).toBe(true)
  })
})
```

- [ ] **Step 2: Run tests and verify failure**

Run: `npm test --workspace @campusmate/web -- --run`

Expected: import failure for `onboardingState`.

- [ ] **Step 3: Implement shared types, state rules, and API client**

Add exact user fields from Task 2 and define:

```ts
export interface OnboardingDraft {
  onboarding_step: number
  onboarding_completed: boolean
  nickname: string
  avatar?: string
  major: string
  grade: string
  interests: string[]
  looking_for: string[]
  skills: string[]
  availability: Record<string, unknown>
  bio?: string
  profile_visibility: Record<string, boolean>
}
```

API functions call `/auth/onboarding` and `/auth/onboarding/complete` through the existing client.

- [ ] **Step 4: Implement the focused wizard shell**

`OnboardingShell` renders the temporary brand mark, six fixed-width progress segments, back button, left task column, and right contextual tip. It must reserve stable column widths so validation messages do not resize the layout.

Use Motion variants:

```ts
const variants = {
  enter: (direction: number) => ({ opacity: 0, x: direction * 16 }),
  center: { opacity: 1, x: 0 },
  exit: (direction: number) => ({ opacity: 0, x: direction * -10 }),
}
```

When reduced motion is active, pass `initial={false}` and use zero translation.

- [ ] **Step 5: Implement all six stages in `Onboarding.tsx`**

Render stages from data rather than six route files. Autosave only on Continue/Back to avoid sending every keystroke. Disable Continue while saving, keep local data on failure, and show a toast without changing steps.

Use standard tag choices already available in `COMMON_SKILLS` plus separate interest and goal lists. Selected chips are solid purple with a remove icon; unselected chips are white with a plus icon. The final step shows a compact public-profile preview and visibility checkboxes.

- [ ] **Step 6: Run unit tests, lint, and build**

Run: `npm test --workspace @campusmate/web -- --run`

Run: `npm run lint --workspace @campusmate/web`

Run: `npm run build --workspace @campusmate/web`

Expected: all commands pass.

- [ ] **Step 7: Commit**

```bash
git add apps/web/src/api/onboarding.ts apps/web/src/pages/Onboarding.tsx apps/web/src/components/onboarding packages/shared/src/types.ts apps/web/src/index.css
git commit -m "feat: add six-step profile onboarding"
```

### Task 6: Enforce Routing and Verify the Complete Flow

**Files:**
- Modify: `apps/web/src/router/index.tsx`
- Modify: `apps/web/src/layouts/MainLayout.tsx`
- Modify: `apps/web/src/store/authStore.ts`
- Create: `apps/web/src/router/authRouting.ts`
- Create: `apps/web/src/router/authRouting.test.ts`
- Modify: `apps/web/src/pages/Onboarding.tsx`
- Test: `tests/test_onboarding_flow.py`

**Interfaces:**
- Consumes: `User.onboarding_completed`, `/onboarding`, and completion API from previous tasks.
- Produces: `requiredRoute(user, requestedPath)` and final route guard behavior.

- [ ] **Step 1: Write failing route-guard tests**

```ts
describe('requiredRoute', () => {
  it('keeps incomplete users inside onboarding', () => {
    expect(requiredRoute({ onboarding_completed: false } as never, '/home')).toBe('/onboarding')
  })

  it('keeps complete users out of onboarding', () => {
    expect(requiredRoute({ onboarding_completed: true } as never, '/onboarding')).toBe('/home')
  })

  it('does not redirect a valid complete-user route', () => {
    expect(requiredRoute({ onboarding_completed: true } as never, '/discover')).toBeNull()
  })
})
```

- [ ] **Step 2: Run route tests and verify failure**

Run: `npm test --workspace @campusmate/web -- --run`

Expected: import failure for `authRouting`.

- [ ] **Step 3: Implement route guards**

Add `/onboarding` outside `MainLayout` but behind authentication. `MainLayout` redirects incomplete users. `Onboarding` redirects complete users to `/home`. Completion replaces the Zustand user with the returned server user before navigating, so the guard never loops.

The pure helper returns only a redirect target or `null`; React components remain responsible for rendering `<Navigate replace />`.

- [ ] **Step 4: Verify backend and frontend suites**

Run: `pytest tests/test_onboarding_flow.py tests/test_auth_verification_flow.py tests/test_auth_lifecycle.py tests/test_migrations.py -q`

Run: `npm test --workspace @campusmate/web -- --run`

Run: `npm run lint --workspace @campusmate/web`

Run: `npm run build --workspace @campusmate/web`

Expected: every command passes.

- [ ] **Step 5: Perform visual and interaction checks**

Start the API with `python src/main.py` and the frontend with `npm run dev --workspace @campusmate/web -- --host 127.0.0.1 --port 5174`. Verify at `1440x900`, `1024x768`, and `390x844`:

- Login shows no verification-code control.
- Registration still sends a campus-email code.
- Successful registration opens stage 1.
- Continue/Back animate in opposite directions.
- Refresh resumes the saved stage.
- Required validation is visible without layout overlap.
- Reduced-motion mode removes horizontal translation.
- Completion opens `/home`; revisiting `/onboarding` returns to `/home`.

- [ ] **Step 6: Commit the integrated phase**

```bash
git add apps/web/src/router/index.tsx apps/web/src/router/authRouting.ts apps/web/src/router/authRouting.test.ts apps/web/src/layouts/MainLayout.tsx apps/web/src/store/authStore.ts apps/web/src/pages/Onboarding.tsx tests/test_onboarding_flow.py
git commit -m "feat: enforce first-login onboarding"
```

### Task 7: Phase-One Review Gate

**Files:**
- Modify only files required by review findings.

**Interfaces:**
- Produces a deployable phase-one branch with no known critical findings.

- [ ] **Step 1: Review the complete branch against the design spec**

Review authentication regressions, migration behavior for existing users, resumability, required-field parity between frontend and backend, keyboard navigation, responsive layout, and reduced-motion behavior.

- [ ] **Step 2: Fix review findings test-first**

For every behavioral finding, add or tighten a focused backend or frontend test, run it to observe failure, implement the correction, and rerun the focused suite.

- [ ] **Step 3: Run the full repository verification**

Run: `pytest -q`

Run: `npm test --workspace @campusmate/web -- --run`

Run: `npm run lint --workspace @campusmate/web`

Run: `npm run build --workspace @campusmate/web`

Run: `git diff --check`

Expected: all commands exit successfully and the worktree is clean after the final commit.

- [ ] **Step 4: Commit review corrections when needed**

```bash
git add -u
git commit -m "fix: address onboarding review findings"
```
