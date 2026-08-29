// =====================
// 共享类型定义
// 前后端共用，角色 B / C / D 协作基础
// =====================

/** 来源类型 */
export type SourceType = 'official' | 'organization' | 'user';

/** 主分类 */
export type MainCategory =
  | '竞赛与项目'
  | '学习与科研'
  | '体育与健身'
  | '旅行与户外'
  | '校园生活'
  | '拼团与AA';

/** 风险等级 */
export type RiskLevel = 'low' | 'medium' | 'high';

/** 帖子状态 */
export type PostStatus = 'recruiting' | 'full' | 'closed' | 'expired';

/** 用户认证状态 */
export type AuthStatus = 'unverified' | 'verified' | 'organization';

/** 帖子结构 */
export interface Post {
  id: string;
  title: string;
  description: string;
  source_type: SourceType;
  main_category: MainCategory;
  tags: string[];
  activity_name: string;
  current_members: number;
  target_members: number;
  needed_roles: string[];
  weekly_hours: string;
  school_scope: string;
  deadline: string;
  risk_level: RiskLevel;
  status: PostStatus;
  author: UserBrief;
  created_at: string;
  match_score?: number;
  match_reason?: string;
}

/** 用户简要信息 */
export interface UserBrief {
  id: string;
  nickname: string;
  avatar?: string;
  auth_status: AuthStatus;
  major?: string;
  grade?: string;
}

/** 用户完整信息 */
export interface User extends UserBrief {
  email: string;
  phone?: string;
  skills: string[];
  verified_email?: string;
  post_count?: number;
  team_count?: number;
}

/** 登录/注册请求 */
export interface LoginRequest {
  account: string; // 手机号或邮箱
  code?: string;   // 验证码
  password?: string;
}

export interface RegisterRequest {
  account: string;
  code: string;
  password?: string;
  nickname: string;
  major: string;
  grade: string;
  skills: string[];
}

/** 认证响应 */
export interface AuthResponse {
  token: string;
  user: User;
}

/** 发帖草稿 */
export interface PostDraft {
  activity_name: string;
  target_members: number;
  needed_roles: string[];
  weekly_hours: string;
  school_scope: string;
  deadline: string;
  description?: string;
}

/** AI 对话消息 */
export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  draft?: PostDraft;
  timestamp: string;
}

/** 发帖 AI 请求 */
export interface PostDraftRequest {
  message: string;
  draft?: PostDraft;
  user_skills?: string[];
}

export interface PostDraftResponse {
  reply: string;
  draft: PostDraft;
  is_complete: boolean;
}

/** 申请结构 */
export interface Application {
  id: string;
  post_id: string;
  applicant: UserBrief;
  role_wanted: string;
  experience: string;
  available_time: string;
  reason: string;
  questions?: string[];
  status: 'pending' | 'accepted' | 'rejected';
  created_at: string;
}

export interface CreateApplicationRequest {
  post_id: string;
  role_wanted: string;
  experience: string;
  available_time: string;
  reason: string;
  questions?: string[];
}

/** 聊天消息 */
export interface Message {
  id: string;
  conversation_id: string;
  sender_id: string;
  content: string;
  created_at: string;
  is_mine: boolean;
}

export interface Conversation {
  id: string;
  post_id: string;
  post_title: string;
  other_user: UserBrief;
  last_message: string;
  last_message_at: string;
  unread_count: number;
  status: 'active' | 'team_confirmed' | 'closed';
  contact_unlocked: boolean;
}

/** 团队 */
export interface Team {
  id: string;
  post_id: string;
  activity_name: string;
  members: TeamMember[];
  division_of_labor: DivisionItem[];
  meeting_agenda: AgendaItem[];
  task_list: TaskItem[];
  risk_reminders: string[];
  contact_info: ContactInfo[];
  created_at: string;
}

export interface TeamMember {
  user: UserBrief;
  suggested_role: string;
}

export interface DivisionItem {
  role: string;
  responsibilities: string;
  member_id?: string;
}

export interface AgendaItem {
  id: string;
  content: string;
  done: boolean;
}

export interface TaskItem {
  id: string;
  title: string;
  assignee_id?: string;
  assignee_name?: string;
  deadline?: string;
  done: boolean;
}

export interface ContactInfo {
  user_id: string;
  nickname: string;
  phone?: string;
  wechat?: string;
}

/** API 统一响应 */
export interface ApiResponse<T = unknown> {
  code: number;
  message: string;
  data: T;
}

/** 分页响应 */
export interface PaginatedResponse<T> {
  list: T[];
  total: number;
  page: number;
  page_size: number;
}
