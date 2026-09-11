const Auth = window.AuthPrototypeState;
let state = Auth.createAuthState();
let panel = 'main';
let errorMessage = '';
let countdown = 0;
let countdownTimer = null;
let previousStage = 0;

const destinationHref = () => window.location.pathname.toLowerCase().includes('campusmate-auth-prototype')
  ? 'CampusMate-interactive-prototype.html'
  : 'topic-and-invitation.html';

const registrationSteps = ['创建账号', '完善资料', '校园认证'];

const stageIndex = () => {
  if (state.authView === 'login' || state.authView === 'register_account') return 0;
  if (state.authView === 'register_profile') return 1;
  if (state.authView === 'campus_verify') return 2;
  return 3;
};

const setState = next => {
  state = next;
  errorMessage = '';
  renderAuthApp();
};

const attempt = action => {
  try {
    setState(action());
  } catch (error) {
    errorMessage = error.message;
    renderAuthApp();
  }
};

const showToast = message => {
  const toast = $('toast');
  toast.textContent = message;
  toast.hidden = false;
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => { toast.hidden = true; }, 2600);
};

const errorBlock = () => errorMessage
  ? `<div class="error-box"><span data-icon="CircleAlert"></span><span>${escapeHTML(errorMessage)}</span></div>`
  : '';

const pageHead = (eyebrow, iconName, title, description) => `
  <header class="page-head">
    <div class="eyebrow"><span data-icon="${iconName}"></span>${escapeHTML(eyebrow)}</div>
    <h1>${escapeHTML(title)}</h1>
    <p>${escapeHTML(description)}</p>
  </header>`;

const renderRegistrationProgress = () => {
  if (!['register_account', 'register_profile', 'campus_verify'].includes(state.authView)) return '';
  const current = stageIndex();
  return `<nav class="registration-progress" aria-label="注册进度"><ol class="progress-list">${registrationSteps.map((label, index) => `<li class="progress-step ${index === current ? 'active' : ''} ${index < current ? 'done' : ''}"><span class="progress-dot"></span><span>${label}</span></li>`).join('')}</ol><div class="registration-privacy"><span data-icon="LockKeyhole"></span><span>校园认证材料仅供审核使用，不进入公开资料，也不交给 AI 处理。</span></div></nav>`;
};

const renderLogin = () => {
  const codeMode = state.loginMode === 'code';
  return `${pageHead('欢迎回来', 'LogIn', '登录 CampusMate', '登录后进入校园组队信息页面；发布、申请和查看联系方式仍需要完成校园认证。')}
    <div class="segmented" role="tablist" aria-label="登录方式">
      <button class="segment ${codeMode ? '' : 'active'}" type="button" data-action="login-mode" data-mode="password">密码登录</button>
      <button class="segment ${codeMode ? 'active' : ''}" type="button" data-action="login-mode" data-mode="code">验证码登录</button>
    </div>
    ${errorBlock()}
    <form class="form" id="login-form">
      <div class="field"><label for="login-account">手机号或邮箱</label><input class="control" id="login-account" name="account" value="student@example.edu.cn" autocomplete="username"></div>
      ${codeMode
        ? `<div class="field"><label for="login-code">验证码</label><div class="input-action"><input class="control" id="login-code" name="code" value="246810" inputmode="numeric" autocomplete="one-time-code"><button class="button secondary" type="button" data-action="send-login-code">发送验证码</button></div></div>`
        : `<div class="field"><label for="login-password">密码</label><input class="control" id="login-password" name="password" type="password" value="DemoPass2026" autocomplete="current-password"></div>`}
      <div class="actions"><button class="button text" type="button" data-action="forgot-password">忘记密码</button><button class="button primary push" type="submit"><span data-icon="LogIn"></span>登录</button></div>
    </form>
    <dl class="demo-credentials"><dt>演示账号</dt><dd>student@example.edu.cn</dd><dt>${codeMode ? '演示验证码' : '演示密码'}</dt><dd>${codeMode ? '246810' : 'DemoPass2026'}</dd></dl>
    <div class="actions"><button class="button secondary" type="button" data-action="start-register"><span data-icon="UserPlus"></span>创建账号</button></div>`;
};

const renderRegisterAccount = () => `${pageHead('第 1 步', 'UserPlus', '创建账号', '手机号或常用邮箱用于登录；创建账号后仍需单独完成校园身份认证。')}
  ${errorBlock()}
  <form class="form" id="register-form">
    <div class="field"><label for="register-account">手机号或邮箱</label><input class="control" id="register-account" name="account" value="student@example.edu.cn" autocomplete="username"></div>
    <div class="field"><label for="register-code">验证码</label><div class="input-action"><input class="control" id="register-code" name="code" value="246810" inputmode="numeric" autocomplete="one-time-code"><button class="button secondary" type="button" data-action="send-register-code">发送验证码</button></div></div>
    <div class="field"><label for="register-password">设置密码</label><input class="control" id="register-password" name="password" type="password" value="DemoPass2026" autocomplete="new-password"><small class="muted">至少 8 位，同时包含字母和数字。</small></div>
    <div class="form-note">注册只建立账号，不会自动获得发帖、申请或组织发布权限。</div>
    <div class="actions"><button class="button text" type="button" data-action="back-login"><span data-icon="ArrowLeft"></span>返回登录</button><button class="button primary push" type="submit">继续完善资料<span data-icon="ArrowRight"></span></button></div>
  </form>`;

const renderProfile = () => `${pageHead('第 2 步', 'UserPlus', '完善个人资料', '昵称用于站内展示；专业、年级和技能可以稍后在个人中心补充。')}
  ${errorBlock()}
  <form class="form" id="profile-form">
    <div class="field"><label for="nickname">昵称</label><input class="control" id="nickname" name="nickname" value="裴同学" autocomplete="nickname"></div>
    <div class="field-row"><div class="field"><label for="major">专业 <span class="optional">选填</span></label><input class="control" id="major" name="major" placeholder="例如：计算机科学"></div><div class="field"><label for="grade">年级 <span class="optional">选填</span></label><select class="control" id="grade" name="grade"><option value="">稍后填写</option><option>2026 级</option><option>2025 级</option><option>2024 级</option><option>研究生</option></select></div></div>
    <div class="field"><label for="skills">技能与兴趣 <span class="optional">选填</span></label><input class="control" id="skills" name="skills" placeholder="例如：Python、摄影、羽毛球"></div>
    <div class="actions"><button class="button text" type="button" data-action="back-register"><span data-icon="ArrowLeft"></span>上一步</button><button class="button primary push" type="submit">进入校园认证<span data-icon="ArrowRight"></span></button></div>
  </form>`;

const renderCampusVerification = () => {
  const sent = state.campusVerification === 'code_sent';
  return `${pageHead('第 3 步', 'GraduationCap', '完成校园身份认证', '认证后可发布个人组队帖、申请加入队伍并在双方确认后查看联系方式。')}
    ${errorBlock()}
    <div class="choice-row">
      <button class="choice" type="button" data-action="focus-campus-email"><span class="choice-icon" data-icon="Mail"></span><span><strong>校园邮箱</strong><p>使用学校分配的 .edu.cn 邮箱接收验证码</p></span></button>
      <button class="choice" type="button" data-action="reserved-sso"><span class="choice-icon" data-icon="KeyRound"></span><span><strong>学校统一身份认证</strong><p>正式版本接入，当前草图仅保留入口</p></span></button>
    </div>
    <form class="form" id="campus-form" style="margin-top:22px">
      <div class="field"><label for="campus-email">校园邮箱</label><div class="input-action"><input class="control" id="campus-email" name="email" value="${escapeHTML(state.campusEmail || 'student@example.edu.cn')}" autocomplete="email"><button class="button secondary" id="campus-send-button" type="button" data-action="send-campus-code" ${countdown ? 'disabled' : ''}>${countdown ? `重新发送 (${countdown}s)` : '发送验证码'}</button></div></div>
      ${sent ? `<div class="success-box"><span data-icon="CheckCircle2"></span><span>验证码已发送至 ${escapeHTML(state.campusEmail)}。演示验证码为 246810。</span></div><div class="field"><label for="campus-code">邮箱验证码</label><input class="control" id="campus-code" name="code" value="246810" inputmode="numeric" autocomplete="one-time-code"></div>` : ''}
      <div class="actions"><button class="button text" type="button" data-action="back-profile"><span data-icon="ArrowLeft"></span>上一步</button>${sent ? '<button class="button primary push" type="submit">完成认证并进入<span data-icon="ArrowRight"></span></button>' : ''}</div>
    </form>`;
};

const statusChip = (text, tone, iconName) => `<span class="status-chip ${tone}"><span data-icon="${iconName}"></span>${escapeHTML(text)}</span>`;

const organizationContent = () => {
  const status = state.organizationApplication;
  const data = state.organizationApplicationData;
  if (panel === 'org-form') return renderOrganizationForm();
  if (status === 'none' || status === 'rejected') return `
    <div class="section-head">${statusChip(status === 'rejected' ? '申请被退回' : '尚未申请', status === 'rejected' ? 'red' : '', status === 'rejected' ? 'XCircle' : 'Circle')}</div>
    <p>${status === 'rejected' ? '请根据审核意见修改组织名称或补充权威来源后重新提交。' : '组织认证用于确认学院、书院、学生组织或社团的真实身份。'}</p>
    <button class="button secondary" type="button" data-action="open-org-form"><span data-icon="Building2"></span>${status === 'rejected' ? '修改并重新申请' : '申请组织认证'}</button>`;
  if (status === 'reviewing') return `
    <div class="section-head">${statusChip('人工审核中', 'amber', 'Clock3')}</div><p>申请不会自动通过。审核人员将核对官方页面、负责人身份和私有证明材料。</p>
    <div class="review-meta"><div><small>申请编号</small><strong>CM-ORG-20260909-014</strong></div><div><small>组织名称</small><strong>${escapeHTML(data.name)}</strong></div><div><small>官方页面</small><strong>${escapeHTML(data.officialPage)}</strong></div><div><small>预计处理</small><strong>2 个工作日内</strong></div></div>
    <div class="simulator"><strong>审核结果模拟</strong><p>正式版本由平台审核员操作；这里用于验证后续界面。</p><div class="actions"><button class="button secondary" type="button" data-action="review-org" data-decision="approved">模拟通过</button><button class="button danger" type="button" data-action="review-org" data-decision="rejected">模拟退回</button></div></div>`;
  return `
    <div class="section-head">${statusChip('组织资质已核验', 'green', 'BadgeCheck')}</div><p>${escapeHTML(data && data.name || '计算机学院学生科创中心')} 已通过资质审核。组织通过不代表当前账号自动获得负责人或发布者角色。</p>
    <div class="review-meta"><div><small>认证有效期</small><strong>2027-09-01</strong></div><div><small>到期处理</small><strong>提前 30 天提醒复核</strong></div></div>
    ${state.organizationRole === 'none' ? `<div class="simulator"><strong>负责人核验模拟</strong><p>正式版本由审核员把首位负责人绑定到组织，不允许用户自行声明“社长”。</p><button class="button secondary" type="button" data-action="grant-owner">模拟核验为负责人</button></div>` : ''}`;
};

const roleContent = () => {
  const labels = { none: '暂无组织角色', member: '组织成员', publisher: '授权发布者', owner: '已核验负责人' };
  const tones = { none: '', member: 'blue', publisher: 'purple', owner: 'green' };
  let html = `<div class="section-head">${statusChip(labels[state.organizationRole], tones[state.organizationRole], state.organizationRole === 'none' ? 'Circle' : 'UserCog')}</div>`;
  if (state.organizationRole === 'none') return `${html}<p>组织审核通过后，仍需由已核验负责人发送站内邀请；接受后角色才生效。</p>`;
  html += `<p>当前权限限定在“计算机学院学生科创中心”，有效期至 2027-09-01，可撤销并保留审计记录。</p>`;
  if (state.organizationRole === 'owner') html += `<button class="button secondary" type="button" data-action="toggle-invite"><span data-icon="Send"></span>${panel === 'invite-form' ? '收起邀请' : '邀请成员或发布者'}</button>`;
  if (state.organizationRole === 'owner' && panel === 'invite-form') html += renderInviteForm();
  if (state.pendingInvite) html += renderInvitePreview();
  return html;
};

const renderIdentityCenter = () => {
  const permissions = Auth.derivePermissions(state);
  const name = state.profile && state.profile.nickname || '裴同学';
  const campusVerified = state.accountStatus === 'campus_verified';
  return `${pageHead('身份与权限', 'ShieldCheck', '认证中心', '账号、校园身份、组织资质和组织角色分别核验，任何一层都不会自动继承更高权限。')}
    <div class="status-band"><span class="avatar">${escapeHTML(name.slice(0,1))}</span><div class="account-meta"><strong>${escapeHTML(name)}</strong><p>${escapeHTML(state.account && state.account.account || 'student@example.edu.cn')}</p></div>${statusChip(campusVerified ? '校园已认证' : '仅账号已注册', campusVerified ? 'green' : 'amber', campusVerified ? 'BadgeCheck' : 'CircleAlert')}</div>
    <div class="identity-sections">
      <section class="identity-section"><div class="section-label"><div><h3>校园身份</h3><p>个人基础权限</p></div></div><div class="section-body"><div class="section-head">${statusChip(campusVerified ? '已认证' : '未认证', campusVerified ? 'green' : 'amber', campusVerified ? 'CheckCircle2' : 'CircleAlert')}</div><p>${campusVerified ? `已通过 ${escapeHTML(state.campusEmail || 'student@example.edu.cn')} 验证。` : '仍可浏览公开内容，发布、申请和联系方式保持锁定。'}</p>${campusVerified ? '' : '<button class="button secondary" type="button" data-action="go-campus">完成校园认证</button>'}<div class="permission-list"><span class="permission on">公开浏览</span><span class="permission ${permissions.canCreateStudentPost ? 'on' : ''}">发布个人组队帖</span><span class="permission ${permissions.canApplyToTeam ? 'on' : ''}">申请加入队伍</span><span class="permission ${permissions.canViewContact ? 'on' : ''}">双方确认后查看联系方式</span></div></div></section>
      <section class="identity-section"><div class="section-label"><div><h3>组织资质</h3><p>主体真实性</p></div></div><div class="section-body">${campusVerified ? organizationContent() : '<p>完成校园认证后才能代表组织提交资质申请。</p>'}</div></section>
      <section class="identity-section"><div class="section-label"><div><h3>组织角色</h3><p>成员与发布权限</p></div></div><div class="section-body">${roleContent()}</div></section>
    </div>
    <div class="actions"><a class="button primary" href="${destinationHref()}"><span data-icon="Compass"></span>进入内容发现页</a><button class="button text" type="button" data-action="logout">退出演示账号</button></div>`;
};

const renderOrganizationForm = () => `${pageHead('组织认证', 'Building2', '提交组织资质申请', '平台核验组织主体后，再由负责人邀请成员和授权发布者。')}
  ${errorBlock()}
  <form class="form" id="organization-form">
    <div class="field-row"><div class="field"><label for="org-type">组织类型</label><select class="control" id="org-type" name="type"><option value="college">学院 / 书院</option><option value="student-org">学生组织</option><option value="club">学生社团</option></select></div><div class="field"><label for="org-school">学校归属</label><input class="control" id="org-school" name="school" value="示例大学"></div></div>
    <div class="field"><label for="org-name">组织标准名称</label><input class="control" id="org-name" name="name" value="计算机学院学生科创中心"></div>
    <div class="field"><label for="org-page">官方页面</label><input class="control" id="org-page" name="officialPage" value="https://example.edu.cn/cs" inputmode="url"><small class="muted">可填写学校官网、学院官网或可公开核验的组织主页。</small></div>
    <div class="field"><label for="org-person">申请负责人</label><input class="control" id="org-person" name="responsiblePerson" value="裴同学"></div>
    <div class="field"><span class="field-label">证明材料 <span class="optional">正式版本私有上传</span></span><div class="file-placeholder"><span data-icon="FileText"></span><span>草图不会读取或上传本地文件。正式版本支持任职证明、指导教师确认或盖章材料。</span></div></div>
    <div class="actions"><button class="button text" type="button" data-action="close-org-form"><span data-icon="ArrowLeft"></span>返回认证中心</button><button class="button primary push" type="submit">提交人工审核<span data-icon="ArrowRight"></span></button></div>
  </form>`;

const renderInviteForm = () => `<form class="form" id="invite-form" style="margin-top:16px">
  <div class="field"><label for="invite-account">受邀人的校园账号</label><input class="control" id="invite-account" name="account" value="member@example.edu.cn"></div>
  <div class="field-row"><div class="field"><label for="invite-role">组织角色</label><select class="control" id="invite-role" name="role"><option value="member">成员</option><option value="publisher">发布者</option></select></div><div class="field"><label for="invite-expiry">权限有效期</label><input class="control" id="invite-expiry" name="expiresAt" type="date" value="2027-09-01"></div></div>
  <button class="button primary" type="submit"><span data-icon="Send"></span>生成站内邀请预览</button>
  <div class="form-note">邀请不会立即赋权。受邀人接受后，权限才在指定组织和有效期内生效。</div>
</form>`;

const renderInvitePreview = () => {
  const invite = state.pendingInvite;
  return `<div class="invite-preview"><h3>待接受的站内邀请</h3><dl><dt>受邀账号</dt><dd>${escapeHTML(invite.account)}</dd><dt>邀请角色</dt><dd>${invite.role === 'publisher' ? '授权发布者' : '组织成员'}</dd><dt>所属组织</dt><dd>计算机学院学生科创中心</dd><dt>有效期至</dt><dd>${escapeHTML(invite.expiresAt)}</dd></dl><div class="actions"><button class="button primary" type="button" data-action="accept-invite">切换为受邀人并接受</button></div></div>`;
};

const renderAuthApp = () => {
  const currentStage = stageIndex();
  const direction = currentStage < previousStage ? 'stage-backward' : '';
  let html;
  if (panel === 'org-form') html = renderOrganizationForm();
  else if (state.authView === 'login') html = renderLogin();
  else if (state.authView === 'register_account') html = renderRegisterAccount();
  else if (state.authView === 'register_profile') html = renderProfile();
  else if (state.authView === 'campus_verify') html = renderCampusVerification();
  else html = renderIdentityCenter();
  $('auth-root').innerHTML = `<div class="stage-panel ${direction}">${html}</div>${renderRegistrationProgress()}`;
  previousStage = currentStage;
  hydrateIcons();
};

const formObject = form => Object.fromEntries(new FormData(form).entries());

const makeRegistered = () => Auth.completeProfile(Auth.registerAccount(Auth.createAuthState(), {
  account: 'student@example.edu.cn', code: '246810', password: 'DemoPass2026'
}), { nickname: '裴同学', major: '计算机科学', grade: '2026 级', skills: 'Python、摄影' });

const makeVerified = () => Auth.verifyCampus(Auth.sendCampusCode(makeRegistered(), 'student@example.edu.cn'), '246810');
const makeReviewing = () => Auth.submitOrganizationApplication(makeVerified(), {
  type: 'college', name: '计算机学院学生科创中心', school: '示例大学',
  officialPage: 'https://example.edu.cn/cs', responsiblePerson: '裴同学'
});
const makeOwner = () => ({ ...Auth.reviewOrganizationApplication(makeReviewing(), 'approved'), organizationRole: 'owner', organizationId: 'org-cs' });

const startCountdown = () => {
  countdown = 60;
  clearInterval(countdownTimer);
  countdownTimer = setInterval(() => {
    countdown -= 1;
    const button = $('campus-send-button');
    if (button) button.textContent = countdown ? `重新发送 (${countdown}s)` : '发送验证码';
    if (!countdown) clearInterval(countdownTimer);
  }, 1000);
};

document.addEventListener('click', event => {
  const button = event.target.closest('[data-action]');
  if (!button) return;
  const action = button.dataset.action;
  if (action === 'login-mode') setState(Auth.setLoginMode(state, button.dataset.mode));
  if (action === 'start-register') setState({ ...Auth.createAuthState(), authView: 'register_account' });
  if (action === 'back-login' || action === 'logout') { panel = 'main'; setState(Auth.createAuthState()); $('demo-state').value = 'visitor'; }
  if (action === 'back-register') setState({ ...state, authView: 'register_account' });
  if (action === 'back-profile') setState({ ...state, authView: 'register_profile' });
  if (action === 'forgot-password') showToast('正式版本将通过独立验证码用途完成密码重置。');
  if (action === 'send-login-code' || action === 'send-register-code') showToast('验证码已发送。演示验证码为 246810。');
  if (action === 'reserved-sso') showToast('学校统一身份认证为正式版本预留入口。');
  if (action === 'focus-campus-email') $('campus-email')?.focus();
  if (action === 'send-campus-code') {
    const email = $('campus-email').value;
    attempt(() => Auth.sendCampusCode(state, email));
    if (!errorMessage) startCountdown();
  }
  if (action === 'go-campus') setState({ ...state, authView: 'campus_verify' });
  if (action === 'open-org-form') { panel = 'org-form'; errorMessage = ''; renderAuthApp(); }
  if (action === 'close-org-form') { panel = 'main'; errorMessage = ''; renderAuthApp(); }
  if (action === 'review-org') attempt(() => Auth.reviewOrganizationApplication(state, button.dataset.decision));
  if (action === 'grant-owner') setState({ ...state, organizationRole: 'owner', organizationId: 'org-cs' });
  if (action === 'toggle-invite') { panel = panel === 'invite-form' ? 'main' : 'invite-form'; renderAuthApp(); }
  if (action === 'accept-invite') { panel = 'main'; attempt(() => Auth.acceptRoleInvite(state)); }
});

document.addEventListener('submit', event => {
  event.preventDefault();
  const form = event.target;
  const data = formObject(form);
  if (form.id === 'login-form') {
    const valid = state.loginMode === 'code' ? data.code === '246810' : data.password === 'DemoPass2026';
    if (!valid) { errorMessage = state.loginMode === 'code' ? '演示验证码为 246810' : '演示密码为 DemoPass2026'; renderAuthApp(); return; }
    window.location.href = destinationHref();
  }
  if (form.id === 'register-form') attempt(() => Auth.registerAccount(state, data));
  if (form.id === 'profile-form') attempt(() => Auth.completeProfile(state, data));
  if (form.id === 'campus-form') {
    try {
      state = Auth.verifyCampus(state, data.code);
      window.location.href = destinationHref();
    } catch (error) {
      errorMessage = error.message;
      renderAuthApp();
    }
  }
  if (form.id === 'organization-form') {
    panel = 'main';
    attempt(() => Auth.submitOrganizationApplication(state, data));
  }
  if (form.id === 'invite-form') attempt(() => Auth.createRoleInvite(state, {
    ...data, organizationId: state.organizationId
  }));
});

$('demo-state').addEventListener('change', event => {
  panel = 'main';
  const presets = {
    visitor: () => Auth.createAuthState(),
    unverified: () => ({ ...Auth.createAuthState(), authView: 'register_account' }),
    verified: () => makeVerified(),
    reviewing: () => makeReviewing(),
    owner: () => makeOwner()
  };
  setState(presets[event.target.value]());
});

$('reset-demo').addEventListener('click', () => {
  panel = 'main';
  countdown = 0;
  clearInterval(countdownTimer);
  $('demo-state').value = 'visitor';
  setState(Auth.resetAuthState(state));
  showToast('演示状态已重置。');
});

hydrateIcons();
renderAuthApp();
