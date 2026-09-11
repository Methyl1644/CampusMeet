initialUsers.operator = {name:'内容运营',major:'CampusMate 内容团队',campus:'不限校区',skills:['来源核验','内容审核'],hours:'工作时间',bio:'负责活动来源核验、重复合并与话题更新。',verified:true};
users.operator ||= structuredClone(initialUsers.operator);

const identityRoles = {
  li:{orgRole:'publisher',orgName:'书友社',orgExpires:'2027-02-28'},
  operator:{siteRole:'operator'}
};
let publishDraft = null;
let publishTopicCandidate = null;
const initialInvitationCount = invitations.length;
const initialTopicTeamCounts = Object.fromEntries(topics.map(topic=>[topic.id,topic.teams.length]));

function resetPublishingDemo(){
  invitations.splice(initialInvitationCount);
  topics.forEach(topic=>topic.teams.splice(initialTopicTeamCounts[topic.id]||0));
  publishDraft=null;
  publishTopicCandidate=null;
}

function publishingIdentity(id=actor){return {verified:user(id).verified,...(identityRoles[id]||{})};}
function identityLabel(id=actor){const identity=publishingIdentity(id);if(identity.siteRole==='operator')return '平台内容运营';if(identity.orgRole)return `${identity.orgName} · 授权发布者`;return identity.verified?'校园已认证':'待校园认证';}
function preparePublishModal(){const modal=$('modal');modal.classList.add('publish-modal');}
function permissionFor(kind){return Publishing.canCreate(publishingIdentity(),kind);}

const publishingCommands = [
  {kind:'clue',icon:'FileText',title:'提交活动线索',description:'提供官网、校院通知或活动页面，交由运营核验收录'},
  {kind:'recruitment',icon:'Users',title:'发起组队招募',description:'选择一个允许组队的话题，再由 AI 整理你的队友需求'},
  {kind:'invitation',icon:'CalendarDays',title:'发起校园搭子',description:'直接发布一次有时间、地点和人数的校内邀约'},
  {kind:'organization_topic',icon:'BadgeCheck',title:'发布组织活动',description:'仅限获得组织发布授权的负责人或发布者'},
  {kind:'official_topic',icon:'ShieldCheck',title:'发布官方话题',description:'核验来源、届次和主办方后建立唯一公共话题'}
];

function openCreateMenu(){
  preparePublishModal();
  const identity=publishingIdentity();
  showModal('创建内容',`<div class="identity-strip">${icon(identity.verified?'BadgeCheck':'CircleAlert')}<div><strong>${displayName(actor)}</strong><small>${escapeHTML(identityLabel())}</small></div><button class="button" type="button" data-identity-center>认证与授权</button></div><div class="command-list">${publishingCommands.map(item=>{const permission=permissionFor(item.kind);return `<button class="command-item" type="button" data-create-kind="${item.kind}" ${permission.allowed?'':`disabled aria-disabled="true"`}><span class="command-icon">${icon(item.icon)}</span><span class="command-copy"><strong>${item.title}</strong><span>${item.description}</span>${permission.allowed?'':`<small>${escapeHTML(permission.reason)}</small>`}</span></button>`;}).join('')}</div>`);
}

function openIdentityCenter(){
  preparePublishModal();
  const identity=publishingIdentity();
  const campusStatus=identity.verified?'已完成':'未完成';
  const orgStatus=identity.orgName?`${identity.orgName}已核验`:'尚未加入认证组织';
  const roleStatus=identity.siteRole==='operator'?'平台内容运营':identity.orgRole?`组织发布者 · 至 ${identity.orgExpires}`:'无组织发布权限';
  showModal('认证与发布权限',`<div class="verification-grid"><section class="verification-card"><header>${icon('GraduationCap')}<strong>校园身份</strong></header><p>通过校园邮箱或学校统一身份页面确认在校身份。</p><span class="badge ${identity.verified?'org':'status'}">${campusStatus}</span></section><section class="verification-card"><header>${icon('Building2')}<strong>组织资质</strong></header><p>学院、书院或社团提交官方页面和证明，由平台人工核验。</p><span class="badge ${identity.orgName?'org':''}">${escapeHTML(orgStatus)}</span></section><section class="verification-card"><header>${icon('ShieldCheck')}<strong>角色授权</strong></header><p>组织通过后，由负责人邀请成员或发布者，权限设有效期。</p><span class="badge ${identity.orgRole||identity.siteRole?'org':'status'}">${escapeHTML(roleStatus)}</span></section></div><div class="verification-flow"><span>提交申请</span>${icon('ChevronRight')}<span>校园邮箱 / 官方页面验证</span>${icon('ChevronRight')}<span>填写或上传证明</span>${icon('ChevronRight')}<span>人工审核</span>${icon('ChevronRight')}<span>设置有效期</span>${icon('ChevronRight')}<span>到期复核</span></div><div class="inline-note">校园认证只开放学生功能，不自动获得代表学院或社团发布话题的权限。证明材料不在公开页面展示。</div>`);
}

function openClueForm(){
  preparePublishModal();
  showModal('提交活动线索',`<p class="topic-form-note">线索不会直接成为公开话题。运营人员将核验来源、届次、主办方并合并重复内容。</p><form id="clue-form"><div class="form-grid"><label class="field full">活动页面或通知链接<input name="source" type="url" required placeholder="https://"></label><label class="field full">你看到的活动名称<input name="title" required maxlength="100" placeholder="活动或比赛名称"></label><label class="field full">补充说明<textarea name="note" maxlength="300" placeholder="可以说明学校、报名截止时间或适合哪些同学"></textarea></label></div><div class="form-actions"><button class="button" type="button" data-create-back>返回</button><button class="button primary" type="submit">提交核验</button></div></form>`);
}

function openDraftIntake(kind,topicId=''){
  preparePublishModal();
  const isRecruitment=kind==='recruitment';
  const allowedTopics=topics.filter(topic=>topic.group);
  const example=isRecruitment?'想参加数学建模，已有会 Python 的同学，还缺论文写作队友':'想在仙林找人打羽球';
  showModal(isRecruitment?'发起组队招募':'发起校园搭子',`<div class="publish-steps"><span class="publish-step active">1 描述需求</span><span class="publish-step">2 AI 补全</span><span class="publish-step">3 确认发布</span></div><div class="composer-layout"><form id="publish-intake" data-kind="${kind}" class="composer-main">${isRecruitment?`<label class="field">关联话题<select name="topicId" required>${allowedTopics.map(topic=>`<option value="${topic.id}" ${topic.id===topicId?'selected':''}>${topic.title}</option>`).join('')}</select></label>`:''}<label class="field">用自己的话描述<textarea class="publish-source" name="description" required maxlength="800">${example}</textarea></label><div class="form-actions"><button class="button" type="button" data-create-back>返回</button><button class="button primary" type="submit">${icon('Sparkles')}让 AI 整理</button></div></form><aside class="composer-side"><h3>本次只整理这些内容</h3><div class="draft-progress"><div class="draft-field"><span>活动或比赛</span><strong>从描述或关联话题获取</strong></div><div class="draft-field"><span>时间与地点</span><strong>可以选择待商定</strong></div><div class="draft-field"><span>人数与要求</span><strong>允许无要求或不知道</strong></div><div class="draft-field"><span>标准标签</span><strong>只能从标签库选择</strong></div></div><div class="ai-boundary">AI 不创建新标签，不认定赛事级别，也不替用户发布。</div></aside></div>`);
}

function statusText(field){return ({answered:'已回答',none:'无要求',unknown:'暂不确定',skipped:'待商定',unasked:'待补充'})[field.status]||field.status;}
function displayField(field){return field.status==='unasked'?'尚未填写':field.value;}
function questionOptions(key){return ({time:[['answer','周五 19:00'],['skip','待商定'],['unknown','暂时不知道']],location:[['answer','仙林校区'],['answer','鼓楼校区'],['answer','线上'],['skip','待商定']],capacity:[['answer','2'],['answer','3'],['answer','4'],['unknown','人数待定']],requirement:[['none','无要求'],['answer','需要基础经验'],['unknown','暂时不知道'],['skip','跳过']]})[key]||[];}

function renderDraftAssistant(){
  preparePublishModal();
  const question=Publishing.nextQuestion(publishDraft);
  if(!question){renderDraftPreview();return;}
  if(state.aiFailure){showModal('AI 整理暂不可用',`<div class="error-band" role="alert">AI 服务异常。草稿仍保留，你可以取消异常开关后重试，正式产品还应提供普通表单作为回退。</div><div class="form-actions"><button class="button" type="button" data-create-back>退出草稿</button><button class="button primary" type="button" data-retry-draft>重试</button></div>`);return;}
  showModal('AI 补全组队信息',`<div class="publish-steps"><span class="publish-step">1 描述需求</span><span class="publish-step active">2 AI 补全</span><span class="publish-step">3 确认发布</span></div><div class="composer-layout"><section class="composer-main"><div class="ai-question"><header>${icon('Sparkles')}只补充一项</header><p>${escapeHTML(question.text)}</p><form id="ai-answer-form" data-field="${question.field}"><label class="field"><input name="answer" maxlength="100" placeholder="直接输入回答"></label><div class="quick-answers">${questionOptions(question.field).map(([action,value])=>`<button type="button" data-draft-answer="${question.field}" data-answer-action="${action}" data-answer-value="${value}">${value}</button>`).join('')}</div><div class="form-actions"><button class="button" type="button" data-create-back>退出草稿</button><button class="button primary" type="submit">继续</button></div></form></div></section><aside class="composer-side"><h3>AI 已整理</h3><div class="draft-progress">${Object.entries(publishDraft.fields).map(([key,value])=>`<div class="draft-field"><span>${({time:'时间',location:'地点',capacity:'团队人数',requirement:'伙伴要求'})[key]}</span><strong>${escapeHTML(displayField(value))}<span class="field-state ${value.status==='unasked'?'pending':''}">${statusText(value)}</span></strong></div>`).join('')}</div><div class="tag-confirm">${publishDraft.tagIds.map(id=>badge(id)).join('')||'<span class="muted small">尚未识别标准标签</span>'}</div></aside></div>`);
}

function renderDraftPreview(){
  preparePublishModal();
  publishDraft.tagIds=Publishing.validateTagIds(publishDraft.tagIds,tags);
  const errors=Publishing.validateForPreview(publishDraft);
  const available=tags.filter(tag=>tag.kind==='topic'&&!publishDraft.tagIds.includes(tag.id)).slice(0,8);
  showModal('确认组队内容',`<div class="publish-steps"><span class="publish-step">1 描述需求</span><span class="publish-step">2 AI 补全</span><span class="publish-step active">3 确认发布</span></div><form id="publish-preview-form"><div class="composer-layout"><section class="composer-main"><label class="field">标题<input name="title" maxlength="80" required value="${escapeHTML(publishDraft.title)}"></label><label class="field">简介<textarea name="summary" maxlength="260" required>${escapeHTML(publishDraft.summary)}</textarea></label><h3>保留的标准标签</h3><div class="tag-confirm">${publishDraft.tagIds.map(id=>`<span class="chip">${escapeHTML(tagById(id).name)}<button type="button" data-draft-remove-tag="${id}" title="移除${escapeHTML(tagById(id).name)}" aria-label="移除${escapeHTML(tagById(id).name)}">${icon('X')}</button></span>`).join('')||'<span class="muted small">请从标签库选择至少一个活动标签</span>'}</div><div class="tag-library"><span class="small muted">标准标签库</span><div>${available.map(tag=>`<button class="button" type="button" data-draft-add-tag="${tag.id}">${icon('Plus')}${tag.name}</button>`).join('')}</div></div></section><aside class="composer-side"><div class="preview-card"><div class="preview-kicker"><span>${publishDraft.kind==='recruitment'?'话题内组队帖':'校园搭子'}</span><span class="badge org">招募中</span></div><h2>${escapeHTML(publishDraft.title)}</h2><p>${escapeHTML(publishDraft.summary)}</p><div class="badges">${publishDraft.tagIds.map(id=>badge(id)).join('')}</div><div class="preview-facts"><div><small>时间</small><strong>${escapeHTML(displayField(publishDraft.fields.time))}</strong></div><div><small>地点</small><strong>${escapeHTML(displayField(publishDraft.fields.location))}</strong></div><div><small>团队人数</small><strong>${escapeHTML(displayField(publishDraft.fields.capacity))}</strong></div><div><small>伙伴要求</small><strong>${escapeHTML(displayField(publishDraft.fields.requirement))}</strong></div></div></div></aside></div><div class="preview-actions"><span class="validation-errors">${errors.map(escapeHTML).join('；')}</span><div><button class="button" type="button" data-edit-draft>返回补充</button> <button class="button primary" type="submit" ${errors.length?'disabled':''}>发布到草图</button></div></div></form>`);
}

function openTopicForm(kind){
  preparePublishModal();
  const identity=publishingIdentity();
  const isOfficial=kind==='official_topic';
  const organizer=isOfficial?'赛事组委会':identity.orgName||'';
  showModal(isOfficial?'建立官方赛事话题':'发布组织活动',`<p class="topic-form-note">同一赛事系列、届次和主办范围只保留一个话题。宣传新闻、延期通知和规则附件应更新原话题。</p><form id="topic-form" data-kind="${kind}"><div class="form-grid"><label class="field">赛事 / 活动系列<input name="title" required value="${isOfficial?'全国大学生数学建模竞赛':'书友社秋季交流会'}"></label><label class="field">届次或学期<input name="edition" required value="2026"></label><label class="field">主办方标识<input name="organizerId" required value="${isOfficial?'mcm-committee':'book-club'}" ${isOfficial?'':'readonly'}></label><label class="field">主办方名称<input name="organizer" required value="${escapeHTML(organizer)}" ${isOfficial?'':'readonly'}></label><label class="field full">来源页面<input name="source" type="url" required value="https://example.edu/activity"></label><label class="field full">内容摘要<textarea name="summary" required maxlength="300">填写活动时间、资格和参与方式，正式发布前仍需核验来源。</textarea></label></div><div id="topic-duplicate-result"></div><div class="form-actions"><button class="button" type="button" data-create-back>返回</button><button class="button primary" type="submit">检查重复并预览</button></div></form>`);
}

function submitDraftToPrototype(){
  const capacity=Math.max(2,Number.parseInt(publishDraft.fields.capacity.value,10)||3);
  const id=`draft-${Date.now()}`;
  if(publishDraft.kind==='invitation'){
    const location=publishDraft.fields.location.value||'待商定';
    const campus=location.includes('鼓楼')?'鼓楼校区':'仙林校区';
    invitations.unshift({id,title:publishDraft.title,tags:[...publishDraft.tagIds],date:'2026-09-12',time:publishDraft.fields.time.value||'待定',end:'待定',campus,place:location,author:user(actor).name,major:user(actor).major,total:capacity,joined:1,summary:publishDraft.summary,requirement:publishDraft.fields.requirement.value||'暂无',cost:'暂无',status:'open'});
    demoStore.posts[id]={id,title:publishDraft.title,owner:actor,capacity,members:[actor],status:'open',roles:['活动伙伴'],summary:publishDraft.summary,kind:'invitation',campus,hours:publishDraft.fields.time.value||'待商定',date:'2026-09-12'};
    state.channel='casual';state.casualMode='daily';state.view='browse';
  }else{
    const topic=topics.find(item=>item.id===publishDraft.topicId);const index=topic.teams.length;
    topic.teams.push({title:publishDraft.title,name:user(actor).name,need:publishDraft.fields.requirement.value||'暂无',summary:publishDraft.summary,slots:`1 / ${capacity} 人`,skills:publishDraft.tagIds.map(id=>tagById(id).name)});
    const postId=`${topic.id}-team-${index}`;
    demoStore.posts[postId]={id:postId,title:publishDraft.title,owner:actor,capacity,members:[actor],status:'open',roles:[publishDraft.fields.requirement.value||'暂无'],summary:publishDraft.summary,topicId:topic.id,kind:'recruitment',campus:publishDraft.fields.location.value||'待商定',hours:publishDraft.fields.time.value||'待商定',date:topic.date};
    state.detailId=topic.id;state.channel=topic.channel;state.subtab='teams';state.view='detail';
  }
  $('modal').close();publishDraft=null;render();window.scrollTo(0,0);toast('已发布到本地草图，不会写入真实数据');
}

const baseRenderGlobalNav=renderGlobalNav;
renderGlobalNav=function(){baseRenderGlobalNav();$('user-verification').textContent=identityLabel();};
const baseRenderProfile=renderProfile;
renderProfile=function(){baseRenderProfile();const host=$('workspace').querySelector('.profile-grid>section');if(host)host.insertAdjacentHTML('beforeend',`<section class="identity-panel"><div class="identity-panel-head"><div><h3>身份与发布权限</h3><p>校园身份、组织资质与组织角色分别核验。</p></div><button class="button" type="button" data-identity-center>${icon('BadgeCheck')}查看认证</button></div></section>`);};
const baseRenderDetail=renderDetail;
renderDetail=function(){baseRenderDetail();const topic=topics.find(item=>item.id===state.detailId);if(!topic?.group)return;const section=$('detail').querySelector('.detail-side .side-section:nth-child(2)');if(section&&!section.querySelector('[data-quick-recruitment]'))section.insertAdjacentHTML('beforeend',`<button type="button" class="button" data-quick-recruitment="${topic.id}" ${permissionFor('recruitment').allowed?'':'disabled'}>${icon('Plus')}发起组队招募</button>`);};

document.addEventListener('click',event=>{
  const button=event.target.closest('button');if(!button)return;
  try{
    if(button.id==='create-button'){openCreateMenu();return;}
    if(button.hasAttribute('data-identity-center')){openIdentityCenter();return;}
    if(button.hasAttribute('data-create-back')){openCreateMenu();return;}
    if(button.dataset.createKind==='clue'){openClueForm();return;}
    if(button.dataset.createKind==='recruitment'){openDraftIntake('recruitment');return;}
    if(button.dataset.createKind==='invitation'){openDraftIntake('invitation');return;}
    if(['organization_topic','official_topic'].includes(button.dataset.createKind)){openTopicForm(button.dataset.createKind);return;}
    if(button.dataset.quickRecruitment){openDraftIntake('recruitment',button.dataset.quickRecruitment);return;}
    if(button.hasAttribute('data-retry-draft')){renderDraftAssistant();return;}
    if(button.dataset.draftAnswer){publishDraft=Publishing.answerDraft(publishDraft,button.dataset.draftAnswer,button.dataset.answerValue,button.dataset.answerAction);renderDraftAssistant();return;}
    if(button.dataset.draftRemoveTag){publishDraft.tagIds=publishDraft.tagIds.filter(id=>id!==button.dataset.draftRemoveTag);renderDraftPreview();return;}
    if(button.dataset.draftAddTag){publishDraft.tagIds=Publishing.validateTagIds([...publishDraft.tagIds,button.dataset.draftAddTag],tags);renderDraftPreview();return;}
    if(button.hasAttribute('data-edit-draft')){const key=Object.keys(publishDraft.fields).find(name=>publishDraft.fields[name].status!=='answered')||'requirement';publishDraft.fields[key].status='unasked';renderDraftAssistant();return;}
    if(button.hasAttribute('data-submit-topic-review')){$('modal').close();toast(publishTopicCandidate.kind==='official_topic'?'官方话题草稿已建立':'组织活动已提交审核');publishTopicCandidate=null;return;}
  }catch(error){toast(error.message);}
});

document.addEventListener('submit',event=>{
  const form=event.target;
  try{
    if(form.id==='publish-intake'){
      event.preventDefault();const data=new FormData(form);const kind=form.dataset.kind;const result=permissionFor(kind);if(!result.allowed)throw new Error(result.reason);
      publishDraft=Publishing.createDraft(kind,data.get('description'),{tags,topicId:data.get('topicId')||null});renderDraftAssistant();return;
    }
    if(form.id==='ai-answer-form'){
      event.preventDefault();const data=new FormData(form);publishDraft=Publishing.answerDraft(publishDraft,form.dataset.field,data.get('answer'),'answer');renderDraftAssistant();return;
    }
    if(form.id==='publish-preview-form'){
      event.preventDefault();const data=new FormData(form);publishDraft.title=String(data.get('title')).trim();publishDraft.summary=String(data.get('summary')).trim();const errors=Publishing.validateForPreview(publishDraft);if(errors.length)throw new Error(errors.join('；'));submitDraftToPrototype();return;
    }
    if(form.id==='clue-form'){
      event.preventDefault();$('modal').close();toast('活动线索已进入核验队列（本地示例）');return;
    }
    if(form.id==='topic-form'){
      event.preventDefault();const data=new FormData(form);const title=String(data.get('title'));const seriesId=/数学建模/.test(title)?'mcm':title.trim().toLowerCase().replace(/\s+/g,'-');const candidate={kind:form.dataset.kind,seriesId,edition:String(data.get('edition')),organizerId:String(data.get('organizerId')),title,organizer:String(data.get('organizer')),source:String(data.get('source')),summary:String(data.get('summary'))};const existing=[{id:'math-2026',seriesId:'mcm',edition:'2026',organizerId:'mcm-committee',title:'大学生数学建模竞赛 · 2026'}];const duplicate=Publishing.findDuplicateTopic(candidate,existing);const result=$('topic-duplicate-result');
      if(duplicate){result.innerHTML=`<div class="duplicate-box"><strong>${icon('CircleAlert')}发现同届同主办话题</strong><p>${duplicate.title} 已存在。应把新来源和规则更新到原话题，不再创建重复话题。</p><button class="button" type="button" data-open="${duplicate.id}">查看已有话题</button></div>`;hydrateIcons();return;}
      publishTopicCandidate=candidate;result.innerHTML=`<div class="preview-card"><div class="preview-kicker"><span>${candidate.kind==='official_topic'?'官方话题草稿':'认证组织活动'}</span><span class="badge status">待核验</span></div><h2>${escapeHTML(candidate.title)} · ${escapeHTML(candidate.edition)}</h2><p>${escapeHTML(candidate.summary)}</p><div class="source-box"><span>${icon('Building2')}${escapeHTML(candidate.organizer)}</span><span>${icon('ExternalLink')}${escapeHTML(candidate.source)}</span></div></div><div class="form-actions"><button class="button primary" type="button" data-submit-topic-review>${candidate.kind==='official_topic'?'建立待发布草稿':'提交人工审核'}</button></div>`;hydrateIcons();return;
    }
  }catch(error){event.preventDefault();toast(error.message);}
});

$('modal').addEventListener('close',()=>{$('modal').classList.remove('publish-modal');});
