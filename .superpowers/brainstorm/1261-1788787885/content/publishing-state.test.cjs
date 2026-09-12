const { test } = require('node:test');
const assert = require('node:assert/strict');
const Publishing = require('./publishing-state.cjs');

const tags = [
  { id: 'badminton', name: '羽毛球', aliases: ['羽球'], active: true },
  { id: 'model', name: '数学建模', aliases: ['数模'], active: true },
  { id: 'retired', name: '旧标签', aliases: [], active: false },
];

test('creation permissions separate campus identity from organization authorization', () => {
  assert.equal(Publishing.canCreate({ verified: false }, 'invitation').allowed, false);
  assert.equal(Publishing.canCreate({ verified: true }, 'invitation').allowed, true);
  assert.equal(Publishing.canCreate({ verified: true }, 'organization_topic').allowed, false);
  assert.equal(Publishing.canCreate({ verified: true, orgRole: 'publisher' }, 'organization_topic').allowed, true);
  assert.equal(Publishing.canCreate({ verified: true, siteRole: 'operator' }, 'official_topic').allowed, true);
});

test('free text is normalized to canonical tag ids without creating tags', () => {
  const draft = Publishing.createDraft('invitation', '周五晚上在仙林找两个人打羽球，水平无所谓', { tags });
  assert.deepEqual(draft.tagIds, ['badminton']);
  assert.equal(draft.fields.requirement.status, 'none');
  assert.equal(draft.fields.requirement.value, '无要求');
  assert.equal(tags.length, 3);
});

test('unknown, none and skipped answers are terminal field states', () => {
  let draft = Publishing.createDraft('invitation', '想找人一起打羽毛球', { tags });
  draft = Publishing.answerDraft(draft, 'time', '', 'unknown');
  draft = Publishing.answerDraft(draft, 'location', '', 'skip');
  draft = Publishing.answerDraft(draft, 'requirement', '', 'none');
  assert.deepEqual(
    [draft.fields.time.status, draft.fields.location.status, draft.fields.requirement.status],
    ['unknown', 'skipped', 'none'],
  );
  assert.notEqual(Publishing.nextQuestion(draft)?.field, 'time');
  assert.notEqual(Publishing.nextQuestion(draft)?.field, 'location');
});

test('inactive and unknown tags are rejected by the whitelist', () => {
  assert.deepEqual(Publishing.validateTagIds(['badminton', 'retired', 'invented'], tags), ['badminton']);
});

test('topic duplicate keys preserve different editions and organizer scopes', () => {
  const a = { seriesId: 'mcm', edition: '2026', organizerId: 'nju' };
  const b = { seriesId: 'mcm', edition: '2027', organizerId: 'nju' };
  assert.equal(Publishing.topicKey(a), 'mcm::2026::nju');
  assert.notEqual(Publishing.topicKey(a), Publishing.topicKey(b));
  assert.equal(Publishing.findDuplicateTopic(a, [{ ...a, id: 'topic-1' }]).id, 'topic-1');
});

test('preview can be generated with explicit pending values but requires core identity fields', () => {
  let draft = Publishing.createDraft('invitation', '想找人一起打羽球', { tags });
  draft = Publishing.answerDraft(draft, 'time', '', 'unknown');
  draft = Publishing.answerDraft(draft, 'location', '', 'skip');
  draft = Publishing.answerDraft(draft, 'capacity', '3', 'answer');
  draft = Publishing.answerDraft(draft, 'requirement', '', 'none');
  assert.deepEqual(Publishing.validateForPreview(draft), []);
  const broken = structuredClone(draft);
  broken.tagIds = [];
  assert.match(Publishing.validateForPreview(broken).join('；'), /活动标签/);
});
