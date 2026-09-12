const test = require('node:test');
const assert = require('node:assert/strict');

const { getSearchSuggestions } = require('./discovery-search.cjs');

const tags = [
  { id: 'model', name: '数学建模', kind: 'topic', aliases: ['数模', '建模'] },
  { id: 'ai', name: '人工智能', kind: 'topic', aliases: ['AI', '智能体'] },
  { id: 'badminton', name: '羽毛球', kind: 'topic', aliases: ['羽球'] }
];

const topics = [
  { id: 'math-2026', channel: 'official', title: '大学生数学建模竞赛 · 2026', short: '数学建模', organizer: '赛事组委会', tags: ['model'] },
  { id: 'ai-2026', channel: 'official', title: '校园 AI 应用创新挑战赛', short: 'AI 应用创新', organizer: '学校教务部门', tags: ['ai'] },
  { id: 'ai-talk', channel: 'organization', title: '计算机学院 AI 实践分享会', short: 'AI 实践分享', organizer: '计算机学院', tags: ['ai'] }
];

const casualItems = [
  { id: 'badminton-evening', title: '今晚体育馆羽毛球双打', tags: ['badminton'] }
];

test('topic keyword aliases return the full official topic title first', () => {
  const result = getSearchSuggestions({ query: '数模', channel: 'official', topics, tags, casualItems: [] });
  assert.equal(result.direct[0].id, 'math-2026');
  assert.equal(result.direct[0].title, '大学生数学建模竞赛 · 2026');
  assert.equal(result.direct[0].kind, 'topic');
});

test('partial title keywords find a topic without requiring the full title', () => {
  const result = getSearchSuggestions({ query: '创新挑战', channel: 'official', topics, tags, casualItems: [] });
  assert.equal(result.direct[0].id, 'ai-2026');
});

test('topic results stay inside the selected official or organization channel', () => {
  const result = getSearchSuggestions({ query: 'AI', channel: 'organization', topics, tags, casualItems: [] });
  assert.deepEqual(result.direct.map(item => item.id), ['ai-talk']);
});

test('casual search returns concrete invitations instead of upper-level topics', () => {
  const result = getSearchSuggestions({ query: '羽球', channel: 'casual', topics, tags, casualItems });
  assert.equal(result.direct[0].id, 'badminton-evening');
  assert.equal(result.direct[0].kind, 'item');
  assert.equal(result.tags[0].id, 'badminton');
});

test('blank queries do not open recommendations', () => {
  const result = getSearchSuggestions({ query: '   ', channel: 'official', topics, tags, casualItems: [] });
  assert.deepEqual(result, { direct: [], tags: [] });
});

