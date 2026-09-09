(function attachAuthPrototypeState(root) {
  const DEMO_CODE = '246810';
  const VALID_ROLES = new Set(['member', 'publisher']);

  const createAuthState = () => ({
    authView: 'login',
    loginMode: 'password',
    accountStatus: 'visitor',
    campusVerification: 'idle',
    organizationApplication: 'none',
    organizationRole: 'none',
    account: null,
    profile: null,
    campusEmail: '',
    organizationApplicationData: null,
    organizationId: null,
    pendingInvite: null
  });

  const requireText = (value, message) => {
    const normalized = String(value || '').trim();
    if (!normalized) throw new Error(message);
    return normalized;
  };

  const isCampusEmail = email => /^[^\s@]+@[^\s@]+\.edu\.cn$/i.test(email);

  const derivePermissions = state => ({
    canBrowse: true,
    canCreateStudentPost: state.accountStatus === 'campus_verified',
    canApplyToTeam: state.accountStatus === 'campus_verified',
    canViewContact: state.accountStatus === 'campus_verified',
    canApplyForOrganization: state.accountStatus === 'campus_verified',
    canPublishOrganizationTopic: state.organizationRole === 'publisher' || state.organizationRole === 'owner',
    canInviteOrganizationRoles: state.organizationRole === 'owner'
  });

  const setLoginMode = (state, loginMode) => {
    if (!['password', 'code'].includes(loginMode)) throw new Error('不支持的登录方式');
    return { ...state, loginMode };
  };

  const registerAccount = (state, payload) => {
    const account = requireText(payload && payload.account, '请输入手机号或邮箱');
    const code = requireText(payload && payload.code, '请输入验证码');
    const password = requireText(payload && payload.password, '请输入密码');
    if (code !== DEMO_CODE) throw new Error('演示验证码为 246810');
    if (password.length < 8 || !/[A-Za-z]/.test(password) || !/\d/.test(password)) {
      throw new Error('密码至少 8 位，并同时包含字母和数字');
    }
    return {
      ...state,
      authView: 'register_profile',
      accountStatus: 'unverified',
      account: { account }
    };
  };

  const completeProfile = (state, payload) => {
    if (state.accountStatus === 'visitor') throw new Error('请先创建账号');
    const nickname = requireText(payload && payload.nickname, '请输入昵称');
    return {
      ...state,
      authView: 'campus_verify',
      profile: {
        nickname,
        major: String(payload.major || '').trim(),
        grade: String(payload.grade || '').trim(),
        skills: String(payload.skills || '').trim()
      }
    };
  };

  const sendCampusCode = (state, email) => {
    if (state.accountStatus === 'visitor') throw new Error('请先登录或注册');
    const normalized = requireText(email, '请输入校园邮箱');
    if (!isCampusEmail(normalized)) throw new Error('请输入以 .edu.cn 结尾的校园邮箱');
    return {
      ...state,
      authView: 'campus_verify',
      campusVerification: 'code_sent',
      campusEmail: normalized
    };
  };

  const verifyCampus = (state, code) => {
    if (state.campusVerification !== 'code_sent') throw new Error('请先向校园邮箱发送验证码');
    if (String(code || '').trim() !== DEMO_CODE) throw new Error('演示验证码为 246810');
    return {
      ...state,
      authView: 'identity_center',
      accountStatus: 'campus_verified',
      campusVerification: 'verified'
    };
  };

  const skipCampusVerification = state => ({ ...state, authView: 'public_browse' });

  const submitOrganizationApplication = (state, payload) => {
    if (state.accountStatus !== 'campus_verified') throw new Error('完成校园认证后才能申请组织认证');
    const data = {
      type: requireText(payload && payload.type, '请选择组织类型'),
      name: requireText(payload && payload.name, '请输入组织标准名称'),
      school: requireText(payload && payload.school, '请输入学校归属'),
      officialPage: requireText(payload && payload.officialPage, '请输入官方页面'),
      responsiblePerson: requireText(payload && payload.responsiblePerson, '请输入负责人姓名')
    };
    return {
      ...state,
      authView: 'identity_center',
      organizationApplication: 'reviewing',
      organizationApplicationData: data
    };
  };

  const reviewOrganizationApplication = (state, decision) => {
    if (state.organizationApplication !== 'reviewing') throw new Error('当前没有待审核的组织申请');
    if (!['approved', 'rejected'].includes(decision)) throw new Error('审核结果无效');
    return {
      ...state,
      authView: 'identity_center',
      organizationApplication: decision,
      organizationId: decision === 'approved' ? 'org-cs' : null,
      organizationRole: 'none'
    };
  };

  const createRoleInvite = (state, payload) => {
    if (state.organizationRole !== 'owner') throw new Error('只有已核验负责人可以邀请组织角色');
    const role = requireText(payload && payload.role, '请选择邀请角色');
    if (!VALID_ROLES.has(role)) throw new Error('只能邀请成员或发布者');
    const organizationId = requireText(payload && payload.organizationId, '邀请必须指定组织');
    if (state.organizationId && state.organizationId !== organizationId) throw new Error('负责人只能管理自己所属的组织');
    return {
      ...state,
      pendingInvite: {
        account: requireText(payload && payload.account, '请输入受邀人的校园账号'),
        role,
        organizationId,
        expiresAt: requireText(payload && payload.expiresAt, '请选择权限有效期')
      }
    };
  };

  const acceptRoleInvite = state => {
    if (!state.pendingInvite) throw new Error('当前没有待接受的邀请');
    return {
      ...state,
      organizationRole: state.pendingInvite.role,
      organizationId: state.pendingInvite.organizationId,
      pendingInvite: null
    };
  };

  const resetAuthState = () => createAuthState();

  const api = {
    DEMO_CODE,
    createAuthState,
    derivePermissions,
    setLoginMode,
    registerAccount,
    completeProfile,
    sendCampusCode,
    verifyCampus,
    skipCampusVerification,
    submitOrganizationApplication,
    reviewOrganizationApplication,
    createRoleInvite,
    acceptRoleInvite,
    resetAuthState
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root) root.AuthPrototypeState = api;
})(typeof window !== 'undefined' ? window : globalThis);
