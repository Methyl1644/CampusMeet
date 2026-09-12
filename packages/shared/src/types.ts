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
export type PostStatus = 'recruiting' | 'full' | 'closed' | 'expired' | 'archived' | 'deleted';

export type ContentChannel = 'official' | 'organization' | 'casual';
export type PostKind = 'topic_team' | 'casual_invitation';
export type FieldStatus = 'confirmed' | 'none' | 'unknown' | 'skipped' | 'pending';

export interface StandardTag {
  tag_id: string;
  canonical_name: string;
  category: string;
  display_color: string;
  matched_alias?: string | null;
}

export interface Topic {
  id: string;
  channel: Exclude<ContentChannel, 'casual'>;
  title: string;
  short_title: string;
  organizer: string;
  edition: string;
  summary: string;
  content: string;
  source_url?: string;
  source_status: string;
  cover_url?: string;
  follower_count: number;
  followed: boolean;
  tags: StandardTag[];
  status: string;
}

export interface SearchDirectResult {
  entity_type: 'topic' | 'post';
  entity_id: string;
  title: string;
  subtitle: string;
  matched_by: string;
  channel: ContentChannel;
}

/** 用户认证状态 */
export type AuthStatus = 'unverified' | 'verified' | 'campus_verified' | 'organization';
export type AccountStatus = 'active' | 'deactivated' | 'deletion_requested' | 'deleted';

/** 帖子结构 */
export interface Post {
  id: string;
  title: string;
  description: string;
  source_type: SourceType;
  kind?: PostKind;
  topic_id?: string | null;
  main_category: MainCategory;
  tags: string[];
  tag_ids?: string[];
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
  account_status?: AccountStatus;
  identity?: IdentitySummary;
}

/** 登录/注册请求 */
export interface LoginRequest {
  account: string; // 手机号或邮箱
  code?: string;   // 验证码
  password?: string;
}

export interface PasswordResetRequest {
  account: string;
  code: string;
  new_password: string;
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
  kind?: PostKind;
  topic_id?: string;
  field_states?: Record<string, { value: string | number | null; status: FieldStatus }>;
}

export interface PostDraftResponse {
  reply: string;
  draft: PostDraft;
  is_complete: boolean;
  field_states?: Record<string, { value: string | number | null; status: FieldStatus }>;
  suggested_tag_ids?: string[];
  candidate_tags?: StandardTag[];
  next_field?: string | null;
  missing_fields?: string[];
  degraded?: boolean;
}

export interface MatchResult {
  user_id?: string;
  candidate_id?: string;
  score: number;
  reason?: string;
  summary?: string;
  acceptability?: 'recommended' | 'conditional' | 'not_recommended';
  hard_conflicts?: string[];
  matched_reasons?: string[];
  potential_risks?: string[];
  suggested_questions?: string[];
}

export interface MatchResponse {
  matches: MatchResult[];
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
  status: 'pending' | 'accepted' | 'rejected' | 'withdrawn';
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
  read_at?: string | null;
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
  owner_id?: string | null;
  status?: 'active' | 'archived';
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
  member_role?: 'owner' | 'member';
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
  due_at?: string;
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

export interface ApiError {
  code: number;
  message: string;
  data: null;
  request_id: string;
}

/** 分页响应 */
export interface PaginatedResponse<T> {
  list: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export type OrganizationRole = 'owner' | 'publisher' | 'member';
export type TopicRole = 'manager' | 'editor' | 'coordinator';
export type PostRole = 'editor' | 'application_manager';
export type PlatformRole = 'operator' | 'senior_operator';
export type GrantStatus = 'pending' | 'active' | 'suspended' | 'revoked' | 'expired';

export interface IdentitySummary {
  campus_verified: boolean;
  organization_roles: Array<{
    organization_id: string;
    organization_name: string;
    role: OrganizationRole;
    expires_at?: string | null;
  }>;
  topic_roles: Array<{ topic_id: string; topic_title: string; role: TopicRole; expires_at?: string | null }>;
  post_roles: Array<{ post_id: string; post_title: string; role: PostRole; expires_at?: string | null }>;
}

export interface ScopedGrant {
  user_id: string;
  role: TopicRole | PostRole;
  status: GrantStatus;
  granted_by: string;
  expires_at?: string | null;
}

export interface PlatformRoleGrant {
  grant_id: string;
  user_id: string;
  role: PlatformRole;
  status: GrantStatus;
  granted_by: string;
  accepted_at?: string | null;
  effective_at?: string | null;
  expires_at?: string | null;
  revoked_at?: string | null;
}

export interface Notification {
  id: string;
  event_type: string;
  title: string;
  body: string;
  target_type?: string | null;
  target_id?: string | null;
  read_at?: string | null;
  created_at: string;
}

export interface Report {
  id: string;
  target_type: 'user' | 'post' | 'topic' | 'message';
  target_id: string;
  reason_code: string;
  description?: string | null;
  report_count: number;
  status: 'pending' | 'resolved' | 'dismissed';
  resolution?: string | null;
  created_at: string;
  resolved_at?: string | null;
}

export interface Appeal {
  id: string;
  case_id: string;
  appellant_id: string;
  statement: string;
  status: 'pending' | 'approved' | 'rejected';
  resolution?: string | null;
  reviewed_by?: string | null;
  created_at: string;
  reviewed_at?: string | null;
}

export interface UploadTicket {
  upload_id: string;
  purpose: 'avatar' | 'topic_cover' | 'organization_evidence';
  expires_at: string;
  upload: {
    url: string;
    method: 'PUT';
    headers: Record<string, string>;
    max_size: number;
  };
}

export interface AccountRequest {
  id: string;
  request_type: 'data_export' | 'account_deletion';
  status: 'pending' | 'completed' | 'cancelled' | 'rejected';
  result_metadata: Record<string, unknown>;
  completed_at?: string | null;
  cancelled_at?: string | null;
  created_at: string;
}
