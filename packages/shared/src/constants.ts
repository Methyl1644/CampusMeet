import type { MainCategory, RiskLevel, SourceType, PostStatus } from './types'

/** 主分类列表 */
export const MAIN_CATEGORIES: MainCategory[] = [
  '竞赛与项目',
  '学习与科研',
  '体育与健身',
  '旅行与户外',
  '校园生活',
  '拼团与AA',
]

/** 来源徽章配置 */
export const SOURCE_BADGE: Record<SourceType, { label: string; color: string }> = {
  official: { label: '官方', color: 'bg-blue-100 text-blue-700' },
  organization: { label: '认证组织', color: 'bg-green-100 text-green-700' },
  user: { label: '个人', color: 'bg-gray-100 text-gray-600' },
}

/** 风险等级配置 */
export const RISK_TAG: Record<RiskLevel, { label: string; color: string }> = {
  low: { label: '正常', color: 'bg-green-100 text-green-700' },
  medium: { label: '需注意', color: 'bg-orange-100 text-orange-700' },
  high: { label: '高风险', color: 'bg-red-100 text-red-700' },
}

/** 帖子状态配置 */
export const POST_STATUS: Record<PostStatus, { label: string; color: string }> = {
  recruiting: { label: '招募中', color: 'bg-green-100 text-green-700' },
  full: { label: '已满员', color: 'bg-gray-100 text-gray-600' },
  closed: { label: '已关闭', color: 'bg-gray-100 text-gray-500' },
  expired: { label: '已截止', color: 'bg-red-100 text-red-600' },
}

/** 首页 Tab 配置 */
export const HOME_TABS = [
  { key: 'recommend', label: '为你推荐' },
  { key: 'recruiting', label: '正在招募' },
  { key: 'official', label: '官方活动' },
  { key: 'hot', label: '校园热门' },
] as const

/** 排序选项 */
export const SORT_OPTIONS = [
  { key: 'latest', label: '最新' },
  { key: 'hot', label: '最热' },
  { key: 'deadline', label: '截止时间' },
] as const

/** 常用技能标签 */
export const COMMON_SKILLS = [
  'Python', 'Java', 'C/C++', 'JavaScript', 'Go',
  '数学建模', '数据分析', '机器学习', '深度学习',
  '英语写作', '论文写作', 'PPT设计', 'UI/UX设计',
  '项目管理', '前端开发', '后端开发', '数据分析',
]

/** API 路径 */
export const API_PATHS = {
  auth: {
    sendCode: '/api/auth/send-code',
    register: '/api/auth/register',
    login: '/api/auth/login',
    verifyEmail: '/api/auth/verify-email',
    profile: '/api/auth/profile',
  },
  posts: {
    list: '/api/posts',
    detail: '/api/posts/:id',
    create: '/api/posts',
    myPosts: '/api/posts/my',
  },
  content: {
    topics: '/api/topics',
    topicDetail: '/api/topics/:id',
    topicPosts: '/api/topics/:id/posts',
    topicFollow: '/api/topics/:id/follow',
    tags: '/api/tags',
    tagSuggestions: '/api/tags/suggestions',
    searchSuggestions: '/api/search/suggestions',
    permissions: '/api/me/permissions',
  },
  agent: {
    postDraft: '/api/agent/post-draft',
    classify: '/api/agent/classify-review',
    match: '/api/agent/match',
    teamPlan: '/api/agent/team-plan',
  },
  applications: {
    create: '/api/applications',
    list: '/api/applications',
    accept: '/api/applications/:id/accept',
    reject: '/api/applications/:id/reject',
    myApplications: '/api/applications/my',
  },
  messages: {
    conversations: '/api/messages/conversations',
    messages: '/api/messages/:conversationId',
    send: '/api/messages/:conversationId/send',
    confirmTeam: '/api/messages/:conversationId/confirm-team',
    close: '/api/messages/:conversationId/close',
  },
  teams: {
    detail: '/api/teams/:id',
    updateTask: '/api/teams/:id/tasks/:taskId',
    myTeams: '/api/teams/my',
  },
} as const
