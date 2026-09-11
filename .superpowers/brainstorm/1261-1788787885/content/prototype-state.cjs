(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.Collaboration = api;
})(typeof window === 'undefined' ? globalThis : window, function () {
  function canViewContact(store, postId, actor) {
    return !!store.teams[postId] && !!store.posts[postId]?.members.includes(actor);
  }
  function reduce(source, action) {
    const store = structuredClone(source);
    if (action.type === 'apply') {
      const post = store.posts[action.postId];
      if (!action.verified) throw new Error('请先完成校园认证');
      if (!post) throw new Error('招募不存在');
      if (post.owner === action.actor) throw new Error('不能申请自己的招募');
      if (post.status !== 'open' || post.members.length >= post.capacity) throw new Error('当前没有可用名额');
      if (post.members.includes(action.actor)) throw new Error('你已在该团队中');
      if (store.applications.some(a => a.postId === post.id && a.applicant === action.actor && ['pending', 'chatting', 'joined'].includes(a.status))) throw new Error('已经申请，请查看申请状态');
      if (['role', 'experience', 'hours', 'reason'].some(key => !action.fields?.[key]?.trim())) throw new Error('请补全角色、经验、时间与原因');
      let id = 'app-' + (store.applications.length + 1);
      while (store.applications.some(a => a.id === id)) id += '-new';
      store.applications.push({ id, postId: post.id, applicant: action.actor, status: 'pending', confirmations: [], fields: action.fields });
      return store;
    }
    const app = store.applications.find(a => a.id === action.appId);
    const post = app && store.posts[app.postId];
    if (!app || !post) throw new Error('申请不存在');
    if (![post.owner, app.applicant].includes(action.actor)) throw new Error('没有操作权限');
    if (['accept', 'reject'].includes(action.type)) {
      if (action.actor !== post.owner) throw new Error('只有发布者有处理权限');
      if (app.status !== 'pending') throw new Error('这条申请已处理');
      if (action.type === 'accept' && (post.status !== 'open' || post.members.length >= post.capacity)) throw new Error('当前没有可用名额');
      app.status = action.type === 'accept' ? 'chatting' : 'rejected';
      if (action.type === 'accept') store.messages[app.id] = [];
    } else if (action.type === 'withdraw') {
      if (action.actor !== app.applicant) throw new Error('只有申请者有撤回权限');
      if (!['pending', 'chatting'].includes(app.status)) throw new Error('申请已结束');
      app.status = 'withdrawn'; app.confirmations = [];
    } else if (action.type === 'close') {
      if (app.status !== 'chatting') throw new Error('沟通已结束');
      app.status = 'closed'; app.confirmations = [];
    } else if (action.type === 'confirm') {
      if (app.status !== 'chatting') throw new Error('需在有效沟通中确认');
      if (post.status !== 'open' || post.members.length >= post.capacity) throw new Error('当前没有可用名额');
      if (!app.confirmations.includes(action.actor)) app.confirmations.push(action.actor);
      if (app.confirmations.includes(post.owner) && app.confirmations.includes(app.applicant)) {
        if (!post.members.includes(app.applicant)) post.members.push(app.applicant);
        app.status = 'joined';
        store.teams[post.id] ||= { postId: post.id, tasks: [], plan: null };
        if (post.members.length >= post.capacity) post.status = 'full';
      }
    } else if (action.type === 'message') {
      if (!['chatting', 'joined'].includes(app.status)) throw new Error('沟通尚未开始或已结束');
      const text = String(action.text || '').trim();
      if (!text) throw new Error('请输入消息');
      const safe = app.status === 'joined' ? text : text.replace(/1[3-9]\d{9}/g, '[联系方式已隐藏]').replace(/(?:微信|wechat|wx|qq)\s*[:：]?\s*[A-Za-z0-9_-]{5,}/gi, '[联系方式已隐藏]');
      (store.messages[app.id] ||= []).push({ from: action.actor, text: safe, time: action.time || '刚刚' });
    } else throw new Error('不支持的操作');
    return store;
  }
  return { reduce, canViewContact };
});
