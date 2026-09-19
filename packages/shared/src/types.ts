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

export type HomeWarningSection =
  | 'deadline_reminder'
  | 'recommended_topics'
  | 'attending_topics'
  | 'followed_topics'
  | 'joined_groups'
  | 'group_timeline'
  | 'unread';

export interface HomeProfile {
  id: string;
  nickname: string;
  avatar: string | null;
  major: string | null;
  grade: string | null;
}

export type HomeTrustBadge =
  | { kind: 'platform_official'; label: string }
  | { kind: 'verified_organization'; label: string; organization_name: string };

export interface HomeResponsiblePerson {
  user_id: string;
  nickname: string;
  role: string;
  badge: string;
}

export interface HomeTag {
  tag_id: string;
  canonical_name: string;
  category: string;
  display_color: string;
}

export interface HomeTopic {
  id: string;
  channel: Exclude<ContentChannel, 'casual'>;
  title: string;
  short_title: string;
  organizer: string;
  edition: string;
  summary: string;
  content: string;
  source_url: string | null;
  source_status: string;
  cover_url: string | null;
  follower_count: number;
  followed: boolean;
  tags: HomeTag[];
  status: 'active';
  trust_badges: HomeTrustBadge[];
  responsible_people: HomeResponsiblePerson[];
  registration_deadline: string | null;
  activity_start_at: string | null;
  activity_end_at: string | null;
}

export interface RecommendedHomeTopic extends HomeTopic {
  recommendation_reason: string;
}

export interface HomeDeadlineReminder extends HomeTopic {
  days_remaining: number;
}

export interface HomeJoinedGroup {
  id: string;
  post_id: string;
  activity_name: string;
  member_role: 'owner' | 'member';
  created_at: string;
  current_members: number;
  target_members: number;
}

export interface HomeTimelineItem {
  team_id: string;
  team_name: string;
  task_id: string;
  title: string;
  due_at: string | null;
  done: boolean;
}

export interface HomeFeed {
  profile: HomeProfile;
  deadline_reminder: HomeDeadlineReminder | null;
  recommended_topics: RecommendedHomeTopic[];
  attending_topics: HomeTopic[];
  followed_topics: HomeTopic[];
  joined_groups: HomeJoinedGroup[];
  group_timeline: HomeTimelineItem[];
  unread: {
    messages: number;
    notifications: number;
  };
  warnings: HomeWarningSection[];
}

export type ParticipationMode = 'open_team' | 'official_signup' | 'information_only';
export type PostPurpose = 'team_recruitment' | 'official_signup' | 'discussion';
export type JoinMode = 'application' | 'direct' | 'none';
export type JoinState = 'owner' | 'joined' | 'pending' | 'rejected' | 'available' | 'closed';

export interface ExploreTag {
  tag_id: string;
  canonical_name: string;
  category: string;
  display_color: string;
}

export interface ExploreUserSummary {
  id: string;
  nickname: string;
  avatar: string | null;
  major: string | null;
  grade: string | null;
}

export type ExploreTrustBadge =
  | { kind: 'platform_official'; label: string }
  | { kind: 'verified_organization'; label: string; organization_name: string };

export interface ExploreResponsiblePerson {
  user_id: string;
  nickname: string;
  role: string;
  badge: string;
}

export interface ExploreLinkedActivity {
  id: string;
  title: string;
  short_title: string;
  organizer: string;
  cover_url: string | null;
  cover_placeholder_key: string;
  registration_deadline: string | null;
  activity_start_at: string | null;
  participation_mode: ParticipationMode;
  status: string;
}

export interface ExploreGroupCard {
  id: string;
  title: string;
  description: string | null;
  source_type: string;
  kind: 'topic_team' | 'casual_invitation';
  purpose: PostPurpose;
  join_mode: JoinMode;
  topic_id: string | null;
  main_category: string;
  activity_name: string;
  cover_url: string | null;
  cover_placeholder_key: string;
  current_members: number;
  target_members: number;
  needed_roles: string[];
  weekly_hours: string | null;
  school_scope: string | null;
  deadline: string | null;
  risk_level: string;
  status: 'recruiting' | 'full' | 'closed';
  author_id: string;
  author: ExploreUserSummary | null;
  bookmark: boolean;
  join_state: JoinState;
  member_preview: ExploreUserSummary[];
  linked_activity: ExploreLinkedActivity | null;
  tags: ExploreTag[];
  collaborators: ExploreResponsiblePerson[];
  created_at: string | null;
}

export interface ExploreGroupDetail extends ExploreGroupCard {}

export interface ExploreActivityCard {
  id: string;
  channel: 'official' | 'organization';
  title: string;
  short_title: string;
  organizer: string;
  edition: string;
  summary: string;
  content: string;
  source_url: string | null;
  source_status: string;
  cover_url: string | null;
  cover_placeholder_key: string;
  location_name: string | null;
  campus_scope: string | null;
  capacity: number | null;
  registration_deadline: string | null;
  activity_start_at: string | null;
  activity_end_at: string | null;
  follower_count: number;
  participant_count: number;
  participant_preview: ExploreUserSummary[];
  participation_mode: ParticipationMode;
  favorite: boolean;
  followed: boolean;
  participation_state: JoinState;
  tags: ExploreTag[];
  status: 'active';
  trust_badges: ExploreTrustBadge[];
  responsible_people: ExploreResponsiblePerson[];
}

export interface ExploreActivityDetail extends ExploreActivityCard {
  related_groups: ExploreGroupCard[];
  can_manage_collaborators: boolean;
}

export interface ExplorePage<T> {
  list: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface TopicFavoriteState {
  topic_id: string;
  favorite: boolean;
  followed: boolean;
  follower_count: number;
}

export interface PostFavoriteState {
  post_id: string;
  bookmark: boolean;
}

export interface DirectJoinResult extends ExploreGroupCard {
  team_id: string;
  member_id: string;
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

export type WeeklyHours =
  | ''
  | '每周 1-3 小时'
  | '每周 4-6 小时'
  | '每周 7-10 小时'
  | '每周 10 小时以上';

export interface OnboardingAvailability {
  weekday_daytime?: boolean;
  weekday_evening?: boolean;
  weekend_daytime?: boolean;
  weekend_evening?: boolean;
  weekly_hours?: WeeklyHours;
}

export interface ProfileVisibility {
  major: boolean;
  grade: boolean;
  interests: boolean;
  skills: boolean;
  availability: boolean;
  contact: boolean;
  activities?: boolean;
  groups?: boolean;
  matching?: boolean;
}

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
  cover_url: string | null;
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
  onboarding_step: number;
  onboarding_completed: boolean;
  bio?: string | null;
  interests: string[];
  looking_for: string[];
  availability: OnboardingAvailability;
  profile_visibility: ProfileVisibility;
  verified_email?: string;
  post_count?: number;
  team_count?: number;
  account_status?: AccountStatus;
  identity?: IdentitySummary;
}

/** 首次资料引导草稿 */
export interface OnboardingDraft {
  onboarding_step: number;
  onboarding_completed: boolean;
  nickname: string;
  avatar?: string;
  major: string;
  grade: string;
  interests: string[];
  looking_for: string[];
  skills: string[];
  availability: OnboardingAvailability;
  bio?: string;
  profile_visibility: ProfileVisibility;
}

/** 首次资料引导保存请求 */
export interface OnboardingUpdate {
  step: number;
  nickname?: string;
  avatar?: string;
  major?: string;
  grade?: string;
  interests?: string[];
  looking_for?: string[];
  skills?: string[];
  availability?: OnboardingAvailability;
  bio?: string;
  profile_visibility?: ProfileVisibility;
}

/** 登录/注册请求 */
export interface LoginRequest {
  account: string;
  password: string;
}

export interface PasswordResetRequest {
  account: string;
  code: string;
  new_password: string;
}

export interface RegisterRequest {
  account: string;
  code: string;
  password: string;
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

export interface WorkflowPostDraft {
  activity?: { value?: string | null; raw_text?: string; confidence?: number };
  time?: { value?: string | null; raw_text?: string; normalized_time?: string; precision?: string; confidence?: number };
  location?: { value?: string | null; raw_text?: string; normalized_location?: string; confidence?: number };
  people?: { total_people?: number | null; current_people?: number | null; recruit_people?: number | null; min_people?: number | null; max_people?: number | null; raw_text?: string; confidence?: number };
  kind?: PostKind;
  topic_id?: string;
  description?: string;
}

export type WorkflowFieldStates = Record<string, { value: unknown; status: FieldStatus }>;

/** AI 对话消息 */
export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  draft?: PostDraft;
  timestamp: string;
}

/** 发帖 AI 请求 */
export interface PostDraftRequest {
  purpose?: PostPurpose;
  publish_context_revision?: string;
  message: string;
  draft?: PostDraft;
  user_skills?: string[];
  kind?: PostKind;
  topic_id?: string;
  field_states?: Record<string, { value: string | number | null; status: FieldStatus }>;
  workflow_draft?: WorkflowPostDraft;
  workflow_field_states?: WorkflowFieldStates;
}

export interface PostDraftResponse {
  blocked?: boolean;
  required_fields?: string[];
  reply: string;
  draft: PostDraft;
  is_complete: boolean;
  field_states?: Record<string, { value: string | number | string[] | null; status: FieldStatus }>;
  workflow_draft?: WorkflowPostDraft;
  workflow_field_states?: WorkflowFieldStates;
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
  nickname?: string;
  major?: string;
  grade?: string;
  interests?: string[];
  skills?: string[];
  availability?: OnboardingAvailability;
  goals?: string[];
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
  my_confirmed?: boolean;
  team_id?: string | null;
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
  is_staff?: boolean;
  platform_role?: PlatformRole | null;
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

export interface ManagementPermissions {
  campus_verified: boolean;
  site_role: string;
  can_publish_post: boolean;
  can_publish_official_topic: boolean;
  publisher_organization_ids: string[];
}

export interface ManagedOrganization {
  organization_id: string;
  organization_name: string;
  role: 'owner';
  expires_at?: string | null;
}

export interface OrganizationApplicationSummary {
  application_id: string;
  organization_name: string;
  org_type: string;
  school_scope?: string | null;
  official_email?: string | null;
  official_page?: string | null;
  status: string;
  review_reason?: string | null;
  reviewed_at?: string | null;
  expires_at?: string | null;
  created_at?: string | null;
}

export interface OrganizationMemberSummary {
  user_id: string;
  role: OrganizationRole;
  status: string;
  effective_at?: string | null;
  expires_at?: string | null;
}

export interface CollaboratorGrant extends ScopedGrant {
  role: TopicRole;
  topic_id?: string;
  accepted_at?: string | null;
  nickname?: string | null;
  is_creator?: boolean;
}

export interface OrganizationInvitationSummary {
  invitation_id: string;
  organization_id: string;
  organization_name?: string;
  inviter_id: string;
  invitee_id: string;
  role: 'publisher' | 'member';
  status: string;
  expires_at: string;
  accepted_at?: string | null;
  created_at?: string | null;
}

export interface TopicCollaborationInvitation extends CollaboratorGrant {
  topic_id: string;
  topic_title: string;
}

export interface PostCollaborationInvitation extends ScopedGrant {
  post_id: string;
  post_title: string;
  role: PostRole;
  accepted_at?: string | null;
}

export interface OwnershipTransferSummary {
  transfer_id: string;
  organization_id: string;
  organization_name?: string;
  from_owner_id: string;
  to_owner_id: string;
  status: string;
  expires_at: string;
  accepted_at?: string | null;
  completed_at?: string | null;
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

export type MyActivityView = 'attending' | 'saved' | 'past';
export type MyGroupView = 'joined' | 'pending' | 'saved' | 'archived';

export interface NotificationPreferences {
  applications: boolean;
  teams: boolean;
  moderation: boolean;
  deadlines: boolean;
  messages: boolean;
}

export interface PublicProfile {
  id: string;
  nickname: string;
  avatar: string | null;
  bio: string | null;
  looking_for: string[];
  major?: string;
  grade?: string;
  interests?: string[];
  skills?: string[];
  availability?: OnboardingAvailability;
  contact?: { wechat?: string };
  activities?: ExploreActivityCard[];
  groups?: ExploreGroupCard[];
  is_owner: boolean;
}

export interface PersonalSettings {
  nickname: string;
  avatar: string | null;
  bio: string | null;
  major: string | null;
  grade: string | null;
  interests: string[];
  looking_for: string[];
  skills: string[];
  availability: OnboardingAvailability;
  profile_visibility: ProfileVisibility;
  notification_preferences: NotificationPreferences;
  wechat?: string | null;
}

export interface PersonalSettingsUpdate {
  nickname?: string;
  avatar?: string | null;
  bio?: string;
  major?: string;
  grade?: string;
  interests?: string[];
  looking_for?: string[];
  skills?: string[];
  availability?: OnboardingAvailability;
  profile_visibility?: Partial<ProfileVisibility>;
  notification_preferences?: Partial<NotificationPreferences>;
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
  purpose: 'avatar' | 'topic_cover' | 'post_cover' | 'organization_evidence';
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
