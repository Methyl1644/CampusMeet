const test = require('node:test');
const assert = require('node:assert/strict');

const {
  createAuthState,
  registerAccount,
  completeProfile,
  sendCampusCode,
  verifyCampus,
  skipCampusVerification,
  submitOrganizationApplication,
  reviewOrganizationApplication,
  createRoleInvite,
  acceptRoleInvite,
  resetAuthState,
  derivePermissions
} = require('./auth-state.cjs');

const registeredState = () => registerAccount(createAuthState(), {
  account: 'student@example.edu.cn',
  code: '246810',
  password: 'DemoPass2026'
});

const verifiedState = () => verifyCampus(
  sendCampusCode(completeProfile(registeredState(), { nickname: '裴同学' }), 'student@example.edu.cn'),
  '246810'
);

const reviewingState = () => submitOrganizationApplication(verifiedState(), {
  type: 'college',
  name: '计算机学院学生科创中心',
  school: '示例大学',
  officialPage: 'https://example.edu.cn/cs',
  responsiblePerson: '裴同学'
});

const ownerState = () => ({
  ...reviewOrganizationApplication(reviewingState(), 'approved'),
  organizationRole: 'owner',
  organizationId: 'org-cs'
});

test('registration creates an unverified account without publishing permission', () => {
  const registered = registeredState();
  assert.equal(registered.accountStatus, 'unverified');
  assert.equal(derivePermissions(registered).canCreateStudentPost, false);
});

test('campus verification unlocks student actions but not organization publishing', () => {
  const verified = verifiedState();
  assert.equal(derivePermissions(verified).canCreateStudentPost, true);
  assert.equal(derivePermissions(verified).canApplyToTeam, true);
  assert.equal(derivePermissions(verified).canPublishOrganizationTopic, false);
});

test('organization approval does not grant a role automatically', () => {
  const approved = reviewOrganizationApplication(reviewingState(), 'approved');
  assert.equal(approved.organizationApplication, 'approved');
  assert.equal(approved.organizationRole, 'none');
});

test('only an owner can create a scoped role invite', () => {
  const publisher = { ...ownerState(), organizationRole: 'publisher' };
  assert.throws(
    () => createRoleInvite(publisher, { account: 'member@example.edu.cn', role: 'publisher', organizationId: 'org-cs', expiresAt: '2027-09-01' }),
    /负责人/
  );

  const invited = createRoleInvite(ownerState(), {
    account: 'member@example.edu.cn',
    role: 'publisher',
    organizationId: 'org-cs',
    expiresAt: '2027-09-01'
  });
  assert.equal(invited.pendingInvite.role, 'publisher');
  assert.equal(invited.pendingInvite.organizationId, 'org-cs');
});

test('accepting an invite grants only its organization-scoped role', () => {
  const invited = createRoleInvite(ownerState(), {
    account: 'member@example.edu.cn',
    role: 'publisher',
    organizationId: 'org-cs',
    expiresAt: '2027-09-01'
  });
  const accepted = acceptRoleInvite(invited);
  assert.equal(accepted.organizationRole, 'publisher');
  assert.equal(accepted.organizationId, 'org-cs');
  assert.equal(accepted.pendingInvite, null);
});

test('skipping campus verification preserves browse-only permissions', () => {
  const skipped = skipCampusVerification(registeredState());
  assert.equal(skipped.authView, 'public_browse');
  assert.equal(derivePermissions(skipped).canBrowse, true);
  assert.equal(derivePermissions(skipped).canCreateStudentPost, false);
});

test('reset clears all fictional account and verification data', () => {
  assert.deepEqual(resetAuthState(ownerState()), createAuthState());
});

