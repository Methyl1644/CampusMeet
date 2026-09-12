(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.Publishing = api;
})(typeof window === 'undefined' ? globalThis : window, function () {
  const questionOrder = ['time', 'location', 'capacity', 'requirement'];
  const labels = {
    time: '计划什么时候进行？',
    location: '计划在哪里进行？',
    capacity: '团队一共需要几人？',
    requirement: '对伙伴有什么要求？',
  };

  function canCreate(identity, kind) {
    if (!identity?.verified) return { allowed: false, reason: '完成校园身份认证后才能创建内容' };
    if (kind === 'organization_topic' && !['publisher', 'owner'].includes(identity.orgRole)) {
      return { allowed: false, reason: '需要认证组织授予发布者权限' };
    }
    if (kind === 'official_topic' && identity.siteRole !== 'operator') {
      return { allowed: false, reason: '只有平台内容运营可以发布官方话题' };
    }
    return { allowed: true, reason: '' };
  }

  function activeTags(tags) {
    return tags.filter(tag => tag.active !== false);
  }

  function tagMatches(text, tag) {
    const source = String(text || '').toLowerCase();
    return [tag.name, ...(tag.aliases || [])].some(name => source.includes(String(name).toLowerCase()));
  }

  function validateTagIds(ids, tags) {
    const allowed = new Set(activeTags(tags).map(tag => tag.id));
    return [...new Set(ids)].filter(id => allowed.has(id));
  }

  function field(value = '', status = 'unasked') {
    return { value, status };
  }

  function createDraft(kind, text, context = {}) {
    const source = String(text || '').trim();
    const tagIds = activeTags(context.tags || []).filter(tag => tagMatches(source, tag)).map(tag => tag.id);
    const requirementNone = /(无所谓|无要求|没有要求|不需要)/.test(source);
    const timeMatch = source.match(/(今天|今晚|明天|周[一二三四五六日天](?:上午|下午|晚上)?|本周末|下周末)/);
    const locationMatch = source.match(/(仙林|鼓楼)(?:校区)?|线上|体育馆|图书馆|篮球场|田径场/);
    const capacityMatch = source.match(/([一二两三四五六七八九十\d]+)个?人/);
    const inferredTitle = kind === 'recruitment'
      ? '寻找一起完成活动的队友'
      : tagIds.length ? `一起${context.tags.find(tag => tag.id === tagIds[0])?.name || '参加活动'}` : '发起一次校园邀约';
    return {
      kind,
      rawText: source,
      title: inferredTitle,
      summary: source,
      topicId: context.topicId || null,
      tagIds,
      fields: {
        time: timeMatch ? field(timeMatch[0], 'answered') : field(),
        location: locationMatch ? field(locationMatch[0].includes('校区') ? locationMatch[0] : locationMatch[0] + (/仙林|鼓楼/.test(locationMatch[0]) ? '校区' : ''), 'answered') : field(),
        capacity: capacityMatch ? field(capacityMatch[1].replace('一', '1').replace('两', '2').replace('二', '2').replace('三', '3').replace('四', '4'), 'answered') : field(),
        requirement: requirementNone ? field('无要求', 'none') : field(),
      },
    };
  }

  function answerDraft(source, key, value, action = 'answer') {
    const draft = structuredClone(source);
    if (!draft.fields[key]) throw new Error('未知字段');
    const terminal = {
      none: { value: key === 'requirement' ? '无要求' : '无', status: 'none' },
      unknown: { value: '暂时不知道', status: 'unknown' },
      skip: { value: '待商定', status: 'skipped' },
    };
    if (terminal[action]) draft.fields[key] = terminal[action];
    else {
      const clean = String(value || '').trim();
      if (!clean) throw new Error('请输入内容，或选择无要求、暂时不知道、待商定');
      draft.fields[key] = { value: clean, status: 'answered' };
    }
    return draft;
  }

  function nextQuestion(draft) {
    const key = questionOrder.find(name => draft.fields[name]?.status === 'unasked');
    return key ? { field: key, text: labels[key] } : null;
  }

  function validateForPreview(draft) {
    const errors = [];
    if (!String(draft.title || '').trim()) errors.push('缺少标题');
    if (!String(draft.summary || '').trim()) errors.push('缺少简介');
    if (!draft.tagIds?.length) errors.push('至少选择一个活动标签');
    if (draft.kind === 'recruitment' && !draft.topicId) errors.push('赛事招募必须关联话题');
    if (draft.fields?.capacity?.status === 'unasked') errors.push('请确认团队人数或标记为待商定');
    return errors;
  }

  function topicKey(topic) {
    return [topic.seriesId, topic.edition, topic.organizerId].map(value => String(value || '').trim().toLowerCase()).join('::');
  }

  function findDuplicateTopic(candidate, topics) {
    const key = topicKey(candidate);
    return topics.find(topic => topicKey(topic) === key) || null;
  }

  return { canCreate, createDraft, answerDraft, nextQuestion, validateTagIds, validateForPreview, topicKey, findDuplicateTopic };
});
