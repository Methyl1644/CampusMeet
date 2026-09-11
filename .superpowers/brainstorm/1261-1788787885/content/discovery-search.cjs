(function attachDiscoverySearch(root) {
  const normalize = value => String(value || '')
    .toLowerCase()
    .replace(/[\s·•—–_\-:：，,。.!！?？()（）\[\]【】]/g, '');

  const textScore = (value, query, exact, starts, contains) => {
    const normalized = normalize(value);
    if (!normalized) return 0;
    if (normalized === query) return exact;
    if (normalized.startsWith(query)) return starts;
    if (normalized.includes(query)) return contains;
    return 0;
  };

  const tagScore = (tag, query) => Math.max(
    textScore(tag.name, query, 76, 68, 60),
    ...(tag.aliases || []).map(alias => textScore(alias, query, 78, 70, 62))
  );

  const recordScore = (record, query, tagMap) => {
    const linkedTagScore = (record.tags || []).reduce((best, id) => {
      const tag = tagMap.get(id);
      return tag ? Math.max(best, tagScore(tag, query)) : best;
    }, 0);
    return Math.max(
      textScore(record.title, query, 100, 94, 88),
      textScore(record.short, query, 98, 92, 86),
      textScore(record.organizer, query, 72, 66, 58),
      linkedTagScore
    );
  };

  const getSearchSuggestions = ({ query, channel, topics = [], tags = [], casualItems = [], selectedTagIds = [] }) => {
    const normalizedQuery = normalize(query);
    if (!normalizedQuery) return { direct: [], tags: [] };
    const tagMap = new Map(tags.map(tag => [tag.id, tag]));
    const source = channel === 'casual'
      ? casualItems.map(item => ({ ...item, kind: 'item' }))
      : topics.filter(topic => topic.channel === channel).map(topic => ({ ...topic, kind: 'topic' }));
    const direct = source
      .map(record => ({ record, score: recordScore(record, normalizedQuery, tagMap) }))
      .filter(entry => entry.score > 0)
      .sort((left, right) => right.score - left.score || left.record.title.localeCompare(right.record.title, 'zh-CN'))
      .slice(0, 5)
      .map(entry => entry.record);
    const selected = new Set(selectedTagIds);
    const matchedTags = tags
      .filter(tag => !selected.has(tag.id))
      .map(tag => ({ tag, score: tagScore(tag, normalizedQuery) }))
      .filter(entry => entry.score > 0)
      .sort((left, right) => right.score - left.score || left.tag.name.localeCompare(right.tag.name, 'zh-CN'))
      .slice(0, 6)
      .map(entry => entry.tag);
    return { direct, tags: matchedTags };
  };

  const api = { getSearchSuggestions, normalize };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root) root.DiscoverySearch = api;
})(typeof window !== 'undefined' ? window : globalThis);

