const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const modulePath = path.join(__dirname, 'prototype-state.cjs');
const api = fs.existsSync(modulePath) ? require(modulePath) : {};
const fixture = () => ({
  posts: { math: { id: 'math', owner: 'wang', capacity: 3, members: ['wang'], status: 'open' } },
  applications: [], messages: {}, teams: {},
});
const apply = (store, user = 'pei') => api.reduce?.(store, { type: 'apply', postId: 'math', actor: user, verified: true, fields: { role: 'Python', experience: '课程项目经验', hours: '每周6小时', reason: '愿意共同完成比赛' } });
const chatting = () => {
  const state = fixture();
  state.applications.push({ id: 'a1', postId: 'math', applicant: 'pei', status: 'chatting', confirmations: [] });
  state.messages.a1 = [];
  return state;
};
test('an application does not add a member or create a team', () => {
  const result = apply(fixture());
  assert.equal(result?.applications[0]?.status, 'pending');
  assert.deepEqual(result.posts.math.members, ['wang']);
  assert.deepEqual(result.teams, {});
});
test('duplicate active applications are rejected', () => {
  const initial = fixture();
  initial.applications.push({ id: 'a1', postId: 'math', applicant: 'pei', status: 'pending', confirmations: [] });
  assert.throws(() => apply(initial), /已经申请/);
});
test('unverified and self applications are rejected', () => {
  assert.throws(() => api.reduce?.(fixture(), { type: 'apply', postId: 'math', actor: 'pei', verified: false, fields: {} }), /校园认证/);
  assert.throws(() => apply(fixture(), 'wang'), /自己的/);
});
test('only the post owner can accept an application', () => {
  const initial = fixture();
  initial.applications.push({ id: 'a1', postId: 'math', applicant: 'pei', status: 'pending', confirmations: [] });
  assert.throws(() => api.reduce?.(initial, { type: 'accept', appId: 'a1', actor: 'li' }), /权限/);
  const result = api.reduce?.(initial, { type: 'accept', appId: 'a1', actor: 'wang' });
  assert.equal(result?.applications[0].status, 'chatting');
  assert.deepEqual(result.messages.a1, []);
});
test('one party cannot complete a team by confirming twice', () => {
  const once = api.reduce?.(chatting(), { type: 'confirm', appId: 'a1', actor: 'pei' });
  const twice = api.reduce?.(once, { type: 'confirm', appId: 'a1', actor: 'pei' });
  assert.deepEqual(twice?.applications[0].confirmations, ['pei']);
  assert.deepEqual(twice.posts.math.members, ['wang']);
  assert.equal(api.canViewContact?.(twice, 'math', 'pei'), false);
});
test('mutual confirmation adds a member but keeps a three-person team open at two', () => {
  const initial = chatting(); initial.applications[0].confirmations = ['pei'];
  const result = api.reduce?.(initial, { type: 'confirm', appId: 'a1', actor: 'wang' });
  assert.deepEqual(result?.posts.math.members, ['wang', 'pei']);
  assert.equal(result.posts.math.status, 'open');
  assert.equal(result.applications[0].status, 'joined');
  assert.equal(api.canViewContact?.(result, 'math', 'pei'), true);
  assert.equal(api.canViewContact?.(result, 'math', 'stranger'), false);
});
test('third member joins the existing team without producing another team', () => {
  const initial = chatting();
  initial.posts.math.members = ['wang', 'li']; initial.teams.math = { postId: 'math', tasks: [] };
  initial.applications[0].confirmations = ['pei'];
  const result = api.reduce?.(initial, { type: 'confirm', appId: 'a1', actor: 'wang' });
  assert.equal(result?.posts.math.status, 'full');
  assert.deepEqual(result.posts.math.members, ['wang', 'li', 'pei']);
  assert.deepEqual(Object.keys(result.teams), ['math']);
});
test('a full post blocks a late confirmation without altering the source', () => {
  const initial = chatting(); initial.posts.math.members = ['wang', 'li', 'lin'];
  assert.throws(() => api.reduce?.(initial, { type: 'confirm', appId: 'a1', actor: 'pei' }), /名额/);
  assert.deepEqual(initial.applications[0].confirmations, []);
});
test('withdrawn applications cannot be confirmed or messaged', () => {
  const initial = chatting(); initial.applications[0].status = 'withdrawn';
  assert.throws(() => api.reduce?.(initial, { type: 'confirm', appId: 'a1', actor: 'wang' }), /沟通/);
  assert.throws(() => api.reduce?.(initial, { type: 'message', appId: 'a1', actor: 'pei', text: '你好' }), /结束/);
});
test('message content is masked before joining and outsiders cannot send', () => {
  assert.throws(() => api.reduce?.(chatting(), { type: 'message', appId: 'a1', actor: 'stranger', text: '你好' }), /权限/);
  const result = api.reduce?.(chatting(), { type: 'message', appId: 'a1', actor: 'pei', text: '手机号 13800000000' });
  assert.equal(result?.messages.a1[0].text, '手机号 [联系方式已隐藏]');
});
