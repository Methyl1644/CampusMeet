# CampusMate Auth Prototype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an independent, editable, single-file CampusMate authentication prototype covering login, registration, campus verification, organization application, and organization role invitation.

**Architecture:** Keep domain transitions in a dependency-free CommonJS state module, render the prototype from a dedicated HTML template plus CSS and browser JavaScript, and assemble the deliverable with the same Node build pattern used by the existing topic prototype. The prototype stores only fictional in-memory state, does not call real APIs, and links into the existing topic prototype after authentication or skip actions.

**Tech Stack:** HTML, CSS, vanilla JavaScript, Node.js CommonJS tests, React server rendering for Lucide icons.

**Spec:** `docs/superpowers/specs/2026-09-09-auth-prototype-design.md`

## Global Constraints

- Do not modify `apps/web/src/pages/Login.tsx`.
- Do not call real APIs, save credentials, or read/upload proof files.
- Use a white background, deep green primary actions, restrained blue/green/purple status colors, and no marketing hero or large gradient.
- Desktop target is 1366px; mobile target is 390px; neither may have horizontal overflow or overlapping text.
- Every page must state that it is a local simulation and must use fictional credentials only.
- Output the editable single-file deliverable to `C:/Users/裴斐/Desktop/EL/work/campusmate-design/CampusMate-auth-prototype.html`.

## File Structure

- Create `.superpowers/brainstorm/1261-1788787885/content/auth-state.cjs`: pure state factory, permission derivation, validation, and transition functions.
- Create `.superpowers/brainstorm/1261-1788787885/content/auth-state.test.cjs`: behavior tests for all permitted and forbidden transitions.
- Create `.superpowers/brainstorm/1261-1788787885/content/auth.template`: semantic page shell and panel containers.
- Create `.superpowers/brainstorm/1261-1788787885/content/auth-ui.css`: responsive authentication and identity-center presentation.
- Create `.superpowers/brainstorm/1261-1788787885/content/auth-ui.js`: browser rendering, form events, demo controls, and navigation.
- Create `.superpowers/brainstorm/1261-1788787885/content/build-auth-prototype.cjs`: icon rendering, source injection, script syntax checks, and HTML generation.
- Generate `.superpowers/brainstorm/1261-1788787885/content/auth-prototype.html`: built preview; do not edit by hand.
- Create `C:/Users/裴斐/Desktop/EL/work/campusmate-design/CampusMate-auth-prototype.html`: user-facing copy of the built preview.
- Update `C:/Users/裴斐/Desktop/EL/work/campusmate-design/interaction-prototype-notes.md`: add the auth prototype entry and explain the simulated boundary.

---

### Task 1: Authentication State Model

**Files:**
- Create: `.superpowers/brainstorm/1261-1788787885/content/auth-state.test.cjs`
- Create: `.superpowers/brainstorm/1261-1788787885/content/auth-state.cjs`

**Interfaces:**
- Produces: `createAuthState()`, `registerAccount(state, payload)`, `completeProfile(state, payload)`, `sendCampusCode(state, email)`, `verifyCampus(state, code)`, `skipCampusVerification(state)`, `submitOrganizationApplication(state, payload)`, `reviewOrganizationApplication(state, decision)`, `createRoleInvite(state, payload)`, `acceptRoleInvite(state)`, `resetAuthState()`, and `derivePermissions(state)`.
- State values follow the exact names in the approved spec: `authView`, `loginMode`, `accountStatus`, `campusVerification`, `organizationApplication`, and `organizationRole`.

- [x] **Step 1: Write failing state-transition tests**

```javascript
test('registration creates an unverified account without publishing permission', () => {
  const registered = registerAccount(createAuthState(), {
    account: 'student@example.edu.cn', code: '246810', password: 'DemoPass2026'
  });
  assert.equal(registered.accountStatus, 'unverified');
  assert.equal(derivePermissions(registered).canCreateStudentPost, false);
});

test('campus verification unlocks student actions but not organization publishing', () => {
  const verified = verifyCampus(sendCampusCode(registeredState(), 'student@example.edu.cn'), '246810');
  assert.equal(derivePermissions(verified).canCreateStudentPost, true);
  assert.equal(derivePermissions(verified).canPublishOrganizationTopic, false);
});

test('organization approval does not grant a role automatically', () => {
  const approved = reviewOrganizationApplication(reviewingOwnerState(), 'approved');
  assert.equal(approved.organizationApplication, 'approved');
  assert.equal(approved.organizationRole, 'none');
});

test('only an owner can create a scoped role invite', () => {
  assert.throws(() => createRoleInvite(publisherState(), { role: 'publisher', organizationId: 'org-cs' }), /负责人/);
  const invited = createRoleInvite(ownerState(), { role: 'publisher', organizationId: 'org-cs', expiresAt: '2027-09-01' });
  assert.equal(invited.pendingInvite.role, 'publisher');
});

test('skipping campus verification preserves browse-only permissions', () => {
  const skipped = skipCampusVerification(registeredState());
  assert.equal(skipped.authView, 'public_browse');
  assert.equal(derivePermissions(skipped).canCreateStudentPost, false);
});

test('reset clears all fictional account and verification data', () => {
  assert.deepEqual(resetAuthState(ownerState()), createAuthState());
});
```

- [x] **Step 2: Run the tests and verify RED**

Run: `node --test .superpowers/brainstorm/1261-1788787885/content/auth-state.test.cjs`

Expected: FAIL because `auth-state.cjs` or its exported functions do not exist.

- [x] **Step 3: Implement the minimal immutable state transitions**

```javascript
const createAuthState = () => ({
  authView: 'login', loginMode: 'password', accountStatus: 'visitor',
  campusVerification: 'idle', organizationApplication: 'none',
  organizationRole: 'none', profile: null, pendingInvite: null
});

const derivePermissions = state => ({
  canBrowse: true,
  canCreateStudentPost: state.accountStatus === 'campus_verified',
  canApplyToTeam: state.accountStatus === 'campus_verified',
  canPublishOrganizationTopic: state.organizationRole === 'publisher' || state.organizationRole === 'owner',
  canInviteOrganizationRoles: state.organizationRole === 'owner'
});
```

Implement every exported transition as a pure function returning a new object. Reject invalid verification codes, non-campus email domains, organization actions from non-verified accounts, and invites created by non-owners with specific Chinese error messages.

- [x] **Step 4: Run the state tests and verify GREEN**

Run: `node --test .superpowers/brainstorm/1261-1788787885/content/auth-state.test.cjs`

Expected: seven tests pass and zero fail.

- [x] **Step 5: Commit the state model**

```bash
git add .superpowers/brainstorm/1261-1788787885/content/auth-state.cjs .superpowers/brainstorm/1261-1788787885/content/auth-state.test.cjs
git commit -m "feat: add auth prototype state model"
```

### Task 2: Login and Registration Experience

**Files:**
- Create: `.superpowers/brainstorm/1261-1788787885/content/auth.template`
- Create: `.superpowers/brainstorm/1261-1788787885/content/auth-ui.css`
- Create: `.superpowers/brainstorm/1261-1788787885/content/auth-ui.js`
- Create: `.superpowers/brainstorm/1261-1788787885/content/build-auth-prototype.cjs`

**Interfaces:**
- Consumes: `window.AuthPrototypeState` exports from Task 1.
- Produces: `renderAuthApp()`, browser event handlers, and placeholder markers `/*ICON_DATA*/`, `/*AUTH_STATE*/`, `/*AUTH_CSS*/`, and `/*AUTH_UI*/` consumed by the build script.

- [x] **Step 1: Extend tests with login-mode and registration validation**

```javascript
test('switching login mode reveals only the selected credential path', () => {
  const state = setLoginMode(createAuthState(), 'code');
  assert.equal(state.loginMode, 'code');
});

test('registration rejects a weak password', () => {
  assert.throws(() => registerAccount(createAuthState(), {
    account: 'student@example.edu.cn', code: '246810', password: '123456'
  }), /密码至少 8 位/);
});
```

- [x] **Step 2: Run tests and verify RED**

Run: `node --test .superpowers/brainstorm/1261-1788787885/content/auth-state.test.cjs`

Expected: FAIL because `setLoginMode` and password-strength validation are missing.

- [x] **Step 3: Implement state support and the login/register UI**

Create a two-column desktop shell with a narrow step rail and one unframed form surface. Add password/code segmented login, forgot-password explanation, public-browse action, account registration, profile completion, inline validation, send-code countdown, back actions, and a persistent “本地模拟，请勿输入真实凭据” notice. The code-login panel must not render a password field; the password-login panel must not render a verification-code field.

- [x] **Step 4: Build and syntax-check the prototype**

Run: `node .superpowers/brainstorm/1261-1788787885/content/build-auth-prototype.cjs`

Expected: prints `Built and syntax-checked` and exits 0.

- [x] **Step 5: Run all state tests**

Run: `node --test .superpowers/brainstorm/1261-1788787885/content/auth-state.test.cjs`

Expected: nine tests pass and zero fail.

- [x] **Step 6: Commit the account experience**

```bash
git add .superpowers/brainstorm/1261-1788787885/content/auth.template .superpowers/brainstorm/1261-1788787885/content/auth-ui.css .superpowers/brainstorm/1261-1788787885/content/auth-ui.js .superpowers/brainstorm/1261-1788787885/content/build-auth-prototype.cjs .superpowers/brainstorm/1261-1788787885/content/auth-prototype.html
git commit -m "feat: build login and registration prototype"
```

### Task 3: Campus and Organization Verification

**Files:**
- Modify: `.superpowers/brainstorm/1261-1788787885/content/auth-state.test.cjs`
- Modify: `.superpowers/brainstorm/1261-1788787885/content/auth-state.cjs`
- Modify: `.superpowers/brainstorm/1261-1788787885/content/auth.template`
- Modify: `.superpowers/brainstorm/1261-1788787885/content/auth-ui.css`
- Modify: `.superpowers/brainstorm/1261-1788787885/content/auth-ui.js`

**Interfaces:**
- Consumes: state transitions and `derivePermissions(state)` from Task 1.
- Produces: campus verification, three-level identity center, organization application review simulator, and owner invitation acceptance flow.

- [x] **Step 1: Add failing validation and permission tests**

```javascript
test('campus verification rejects an unapproved email domain', () => {
  assert.throws(() => sendCampusCode(registeredState(), 'student@gmail.com'), /校园邮箱/);
});

test('an accepted invite grants only its organization-scoped role', () => {
  const accepted = acceptRoleInvite(invitedMemberState());
  assert.equal(accepted.organizationRole, 'publisher');
  assert.equal(accepted.organizationId, 'org-cs');
});
```

- [x] **Step 2: Run tests and verify RED**

Run: `node --test .superpowers/brainstorm/1261-1788787885/content/auth-state.test.cjs`

Expected: FAIL on domain rejection or organization scope until both behaviors exist.

- [x] **Step 3: Implement verification views**

Render campus email verification with code-sent/error/success states; render identity center with separate campus, organization, and role status sections; render organization type/name/school/official-page/responsible-person forms; render a non-reading file chooser placeholder; render reviewing/approved/rejected simulations; and render owner-only member/publisher invites with organization and expiry shown before acceptance.

- [x] **Step 4: Rebuild and run tests**

Run: `node .superpowers/brainstorm/1261-1788787885/content/build-auth-prototype.cjs`

Run: `node --test .superpowers/brainstorm/1261-1788787885/content/auth-state.test.cjs`

Expected: build exits 0 and ten tests pass.

- [x] **Step 5: Commit verification flows**

```bash
git add .superpowers/brainstorm/1261-1788787885/content/auth-state.cjs .superpowers/brainstorm/1261-1788787885/content/auth-state.test.cjs .superpowers/brainstorm/1261-1788787885/content/auth.template .superpowers/brainstorm/1261-1788787885/content/auth-ui.css .superpowers/brainstorm/1261-1788787885/content/auth-ui.js .superpowers/brainstorm/1261-1788787885/content/auth-prototype.html
git commit -m "feat: add campus and organization verification flows"
```

### Task 4: Deliverable Copy and Browser Verification

**Files:**
- Copy generated file to: `C:/Users/裴斐/Desktop/EL/work/campusmate-design/CampusMate-auth-prototype.html`
- Modify: `C:/Users/裴斐/Desktop/EL/work/campusmate-design/interaction-prototype-notes.md`

**Interfaces:**
- Consumes: built `auth-prototype.html` from Task 3 and existing `CampusMate-interactive-prototype.html`.
- Produces: final user-facing auth prototype with a relative link to `CampusMate-interactive-prototype.html`.

- [x] **Step 1: Copy the generated HTML and document its scope**

Use PowerShell `Copy-Item -LiteralPath` to copy the built HTML. In the notes, list the two prototypes, explain that all identity states are simulated, and record that production work still requires OTP separation, school-domain configuration, organization models/APIs, audit logs, and JWT lifecycle handling.

- [x] **Step 2: Run fresh automated verification**

Run: `node --test .superpowers/brainstorm/1261-1788787885/content/auth-state.test.cjs .superpowers/brainstorm/1261-1788787885/content/prototype-state.test.cjs .superpowers/brainstorm/1261-1788787885/content/publishing-state.test.cjs`

Run: `node .superpowers/brainstorm/1261-1788787885/content/build-auth-prototype.cjs`

Expected: all tests pass, build exits 0, and the output reports successful syntax checking.

- [x] **Step 3: Verify required desktop interactions at 1366px**

Open `http://127.0.0.1:53806/auth-prototype.html` and verify: password/code switching; registration; profile completion; skip campus verification; successful campus verification using fictional code `246810`; organization application reviewing/approved/rejected states; owner invitation; invited user acceptance; reset; and link into the topic prototype. Confirm no console errors or warnings.

- [x] **Step 4: Verify responsive layout at 390px**

Resize to 390px and confirm: the left rail becomes a compact top stepper; inputs and buttons stay within the viewport; status labels wrap cleanly; no horizontal scrollbar appears; and the fixed actions do not cover form content.

- [x] **Step 5: Inspect workspace changes**

Run: `git diff --check`

Run: `git status --short`

Expected: no whitespace errors; existing user change in `apps/web/src/pages/Login.tsx` remains untouched; only intended prototype sources, generated output, and notes are new or modified.

- [x] **Step 6: Commit documentation changes inside the repository**

```bash
git add docs/superpowers/plans/2026-09-09-auth-prototype-implementation.md
git commit -m "docs: add auth prototype implementation plan"
```
