import { API_PATHS } from '@shared/constants'
import type {
  ApiResponse,
  DirectJoinResult,
  ExploreActivityCard,
  ExploreActivityDetail,
  ExploreGroupCard,
  ExploreGroupDetail,
  ExploreLinkedActivity,
  ExplorePage,
  ExploreResponsiblePerson,
  ExploreTag,
  ExploreTrustBadge,
  ExploreUserSummary,
  JoinMode,
  JoinState,
  ParticipationMode,
  PostFavoriteState,
  PostPurpose,
  TopicFavoriteState,
} from '@shared/types'
import { client } from './client'

export interface ExploreActivityListParams {
  query?: string
  tagIds?: string[]
  date?: '' | 'upcoming' | 'registration_open' | 'past'
  status?: '' | 'registration_open' | 'ended'
  type?: '' | 'official' | 'organization' | ParticipationMode
  campus?: string
  page?: number
  pageSize?: number
}

export interface ExploreGroupListParams {
  query?: string
  tagIds?: string[]
  date?: '' | 'upcoming' | 'past'
  status?: '' | 'recruiting' | 'full' | 'closed'
  type?: '' | PostPurpose | 'topic_team' | 'casual_invitation'
  campus?: string
  page?: number
  pageSize?: number
}

export interface RelatedGroupListParams {
  purpose?: PostPurpose
  page?: number
  pageSize?: number
}

export class ExploreContractError extends Error {
  constructor(path: string, expected: string) {
    super(`Invalid Explore response at ${path}: expected ${expected}`)
    this.name = 'ExploreContractError'
  }
}

type RecordValue = Record<string, unknown>
type Decoder<T> = (value: unknown, path: string) => T

const participationModes = new Set<ParticipationMode>([
  'open_team', 'official_signup', 'information_only',
])
const postPurposes = new Set<PostPurpose>([
  'team_recruitment', 'official_signup', 'discussion',
])
const joinModes = new Set<JoinMode>(['application', 'direct', 'none'])
const joinStates = new Set<JoinState>([
  'owner', 'joined', 'pending', 'rejected', 'available', 'closed',
])

function record(value: unknown, path: string): RecordValue {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new ExploreContractError(path, 'object')
  }
  return value as RecordValue
}

function string(value: unknown, path: string): string {
  if (typeof value !== 'string') throw new ExploreContractError(path, 'string')
  return value
}

function nullableString(value: unknown, path: string): string | null {
  return value === null ? null : string(value, path)
}

function boolean(value: unknown, path: string): boolean {
  if (typeof value !== 'boolean') throw new ExploreContractError(path, 'boolean')
  return value
}

function integer(value: unknown, path: string, minimum = 0): number {
  if (!Number.isInteger(value) || (value as number) < minimum) {
    throw new ExploreContractError(path, `integer >= ${minimum}`)
  }
  return value as number
}

function nullablePositiveInteger(value: unknown, path: string): number | null {
  return value === null ? null : integer(value, path, 1)
}

function literal<T extends string>(
  value: unknown,
  path: string,
  values: ReadonlySet<T>,
): T {
  if (typeof value !== 'string' || !values.has(value as T)) {
    throw new ExploreContractError(path, [...values].join(' | '))
  }
  return value as T
}

function array<T>(value: unknown, path: string, decode: Decoder<T>, maximum?: number): T[] {
  if (!Array.isArray(value) || (maximum !== undefined && value.length > maximum)) {
    throw new ExploreContractError(path, maximum === undefined ? 'array' : `array of at most ${maximum}`)
  }
  return value.map((item, index) => decode(item, `${path}[${index}]`))
}

function decodeTag(value: unknown, path: string): ExploreTag {
  const item = record(value, path)
  return {
    tag_id: string(item.tag_id, `${path}.tag_id`),
    canonical_name: string(item.canonical_name, `${path}.canonical_name`),
    category: string(item.category, `${path}.category`),
    display_color: string(item.display_color, `${path}.display_color`),
  }
}

function decodeUser(value: unknown, path: string): ExploreUserSummary {
  const item = record(value, path)
  return {
    id: string(item.id, `${path}.id`),
    nickname: string(item.nickname, `${path}.nickname`),
    avatar: nullableString(item.avatar, `${path}.avatar`),
    major: nullableString(item.major, `${path}.major`),
    grade: nullableString(item.grade, `${path}.grade`),
  }
}

function decodeResponsiblePerson(value: unknown, path: string): ExploreResponsiblePerson {
  const item = record(value, path)
  return {
    user_id: string(item.user_id, `${path}.user_id`),
    nickname: string(item.nickname, `${path}.nickname`),
    role: string(item.role, `${path}.role`),
    badge: string(item.badge, `${path}.badge`),
  }
}

function decodeTrustBadge(value: unknown, path: string): ExploreTrustBadge {
  const item = record(value, path)
  const kind = literal(
    item.kind,
    `${path}.kind`,
    new Set(['platform_official', 'verified_organization'] as const),
  )
  const label = string(item.label, `${path}.label`)
  if (kind === 'platform_official') return { kind, label }
  return {
    kind,
    label,
    organization_name: string(item.organization_name, `${path}.organization_name`),
  }
}

function decodeLinkedActivity(value: unknown, path: string): ExploreLinkedActivity {
  const item = record(value, path)
  return {
    id: string(item.id, `${path}.id`),
    title: string(item.title, `${path}.title`),
    short_title: string(item.short_title, `${path}.short_title`),
    organizer: string(item.organizer, `${path}.organizer`),
    cover_url: nullableString(item.cover_url, `${path}.cover_url`),
    cover_placeholder_key: string(item.cover_placeholder_key, `${path}.cover_placeholder_key`),
    registration_deadline: nullableString(item.registration_deadline, `${path}.registration_deadline`),
    activity_start_at: nullableString(item.activity_start_at, `${path}.activity_start_at`),
    participation_mode: literal(
      item.participation_mode,
      `${path}.participation_mode`,
      participationModes,
    ),
    status: string(item.status, `${path}.status`),
  }
}

function decodeGroup(value: unknown, path: string): ExploreGroupCard {
  const item = record(value, path)
  return {
    id: string(item.id, `${path}.id`),
    title: string(item.title, `${path}.title`),
    description: nullableString(item.description, `${path}.description`),
    source_type: string(item.source_type, `${path}.source_type`),
    kind: literal(item.kind, `${path}.kind`, new Set(['topic_team', 'casual_invitation'] as const)),
    purpose: literal(item.purpose, `${path}.purpose`, postPurposes),
    join_mode: literal(item.join_mode, `${path}.join_mode`, joinModes),
    topic_id: nullableString(item.topic_id, `${path}.topic_id`),
    main_category: string(item.main_category, `${path}.main_category`),
    activity_name: string(item.activity_name, `${path}.activity_name`),
    cover_url: nullableString(item.cover_url, `${path}.cover_url`),
    cover_placeholder_key: string(item.cover_placeholder_key, `${path}.cover_placeholder_key`),
    current_members: integer(item.current_members, `${path}.current_members`),
    target_members: integer(item.target_members, `${path}.target_members`, 1),
    needed_roles: array(item.needed_roles, `${path}.needed_roles`, string),
    weekly_hours: nullableString(item.weekly_hours, `${path}.weekly_hours`),
    school_scope: nullableString(item.school_scope, `${path}.school_scope`),
    deadline: nullableString(item.deadline, `${path}.deadline`),
    risk_level: string(item.risk_level, `${path}.risk_level`),
    status: literal(item.status, `${path}.status`, new Set(['recruiting', 'full', 'closed'] as const)),
    author_id: string(item.author_id, `${path}.author_id`),
    author: item.author === null ? null : decodeUser(item.author, `${path}.author`),
    bookmark: boolean(item.bookmark, `${path}.bookmark`),
    join_state: literal(item.join_state, `${path}.join_state`, joinStates),
    member_preview: array(item.member_preview, `${path}.member_preview`, decodeUser, 8),
    linked_activity: item.linked_activity === null
      ? null
      : decodeLinkedActivity(item.linked_activity, `${path}.linked_activity`),
    tags: array(item.tags, `${path}.tags`, decodeTag),
    collaborators: array(item.collaborators, `${path}.collaborators`, decodeResponsiblePerson),
    created_at: nullableString(item.created_at, `${path}.created_at`),
  }
}

function decodeActivityCard(value: unknown, path: string): ExploreActivityCard {
  const item = record(value, path)
  return {
    id: string(item.id, `${path}.id`),
    channel: literal(item.channel, `${path}.channel`, new Set(['official', 'organization'] as const)),
    title: string(item.title, `${path}.title`),
    short_title: string(item.short_title, `${path}.short_title`),
    organizer: string(item.organizer, `${path}.organizer`),
    edition: string(item.edition, `${path}.edition`),
    summary: string(item.summary, `${path}.summary`),
    content: string(item.content, `${path}.content`),
    source_url: nullableString(item.source_url, `${path}.source_url`),
    source_status: string(item.source_status, `${path}.source_status`),
    cover_url: nullableString(item.cover_url, `${path}.cover_url`),
    cover_placeholder_key: string(item.cover_placeholder_key, `${path}.cover_placeholder_key`),
    location_name: nullableString(item.location_name, `${path}.location_name`),
    campus_scope: nullableString(item.campus_scope, `${path}.campus_scope`),
    capacity: nullablePositiveInteger(item.capacity, `${path}.capacity`),
    registration_deadline: nullableString(item.registration_deadline, `${path}.registration_deadline`),
    activity_start_at: nullableString(item.activity_start_at, `${path}.activity_start_at`),
    activity_end_at: nullableString(item.activity_end_at, `${path}.activity_end_at`),
    follower_count: integer(item.follower_count, `${path}.follower_count`),
    participant_count: integer(item.participant_count, `${path}.participant_count`),
    participant_preview: array(item.participant_preview, `${path}.participant_preview`, decodeUser, 8),
    participation_mode: literal(
      item.participation_mode,
      `${path}.participation_mode`,
      participationModes,
    ),
    favorite: boolean(item.favorite, `${path}.favorite`),
    followed: boolean(item.followed, `${path}.followed`),
    participation_state: literal(item.participation_state, `${path}.participation_state`, joinStates),
    tags: array(item.tags, `${path}.tags`, decodeTag),
    status: literal(item.status, `${path}.status`, new Set(['active'] as const)),
    trust_badges: array(item.trust_badges, `${path}.trust_badges`, decodeTrustBadge),
    responsible_people: array(
      item.responsible_people,
      `${path}.responsible_people`,
      decodeResponsiblePerson,
    ),
  }
}

function decodeActivityDetail(value: unknown, path: string): ExploreActivityDetail {
  const item = record(value, path)
  return {
    ...decodeActivityCard(item, path),
    related_groups: array(item.related_groups, `${path}.related_groups`, decodeGroup, 8),
  }
}

function decodePage<T>(decodeItem: Decoder<T>, maximum: number): Decoder<ExplorePage<T>> {
  return (value, path) => {
    const item = record(value, path)
    const pageSize = integer(item.page_size, `${path}.page_size`, 1)
    if (pageSize > maximum) {
      throw new ExploreContractError(`${path}.page_size`, `integer <= ${maximum}`)
    }
    return {
      list: array(item.list, `${path}.list`, decodeItem),
      total: integer(item.total, `${path}.total`),
      page: integer(item.page, `${path}.page`, 1),
      page_size: pageSize,
      pages: integer(item.pages, `${path}.pages`),
    }
  }
}

function decodeEnvelope<T>(value: unknown, decode: Decoder<T>): T {
  const envelope = record(value, 'response')
  if (envelope.code !== 0) throw new ExploreContractError('response.code', '0')
  string(envelope.message, 'response.message')
  return decode(envelope.data, 'response.data')
}

function listParams(params: ExploreActivityListParams | ExploreGroupListParams) {
  const values: Record<string, unknown> = {
    q: params.query,
    tag_ids: params.tagIds?.join(','),
    date: params.date,
    status: params.status,
    type: params.type,
    campus: params.campus,
    page: params.page,
    page_size: params.pageSize,
  }
  return Object.fromEntries(Object.entries(values).filter(([, value]) => value !== undefined))
}

export async function listExploreActivities(
  params: ExploreActivityListParams = {},
  signal?: AbortSignal,
): Promise<ExplorePage<ExploreActivityCard>> {
  const response = await client.get<ApiResponse<unknown>>(API_PATHS.explore.activities, {
    params: listParams(params),
    signal,
  })
  return decodeEnvelope(response.data, decodePage(decodeActivityCard, 40))
}

export async function getExploreActivity(
  id: string,
  signal?: AbortSignal,
): Promise<ExploreActivityDetail> {
  const response = await client.get<ApiResponse<unknown>>(
    API_PATHS.explore.activityDetail.replace(':id', id),
    { signal },
  )
  return decodeEnvelope(response.data, decodeActivityDetail)
}

export async function listExploreGroups(
  params: ExploreGroupListParams = {},
  signal?: AbortSignal,
): Promise<ExplorePage<ExploreGroupCard>> {
  const response = await client.get<ApiResponse<unknown>>(API_PATHS.explore.groups, {
    params: listParams(params),
    signal,
  })
  return decodeEnvelope(response.data, decodePage(decodeGroup, 40))
}

export async function getExploreGroup(
  id: string,
  signal?: AbortSignal,
): Promise<ExploreGroupDetail> {
  const response = await client.get<ApiResponse<unknown>>(
    API_PATHS.explore.groupDetail.replace(':id', id),
    { signal },
  )
  return decodeEnvelope(response.data, decodeGroup)
}

export async function setActivityFavorite(
  id: string,
  favorite: boolean,
  signal?: AbortSignal,
): Promise<TopicFavoriteState> {
  const path = API_PATHS.explore.favoriteActivity.replace(':id', id)
  const response = favorite
    ? await client.put<ApiResponse<unknown>>(path, undefined, { signal })
    : await client.delete<ApiResponse<unknown>>(path, { signal })
  return decodeEnvelope(response.data, (value, valuePath) => {
    const item = record(value, valuePath)
    return {
      topic_id: string(item.topic_id, `${valuePath}.topic_id`),
      favorite: boolean(item.favorite, `${valuePath}.favorite`),
      followed: boolean(item.followed, `${valuePath}.followed`),
      follower_count: integer(item.follower_count, `${valuePath}.follower_count`),
    }
  })
}

export async function setGroupFavorite(
  id: string,
  favorite: boolean,
  signal?: AbortSignal,
): Promise<PostFavoriteState> {
  const path = API_PATHS.explore.favoriteGroup.replace(':id', id)
  const response = favorite
    ? await client.put<ApiResponse<unknown>>(path, undefined, { signal })
    : await client.delete<ApiResponse<unknown>>(path, { signal })
  return decodeEnvelope(response.data, (value, valuePath) => {
    const item = record(value, valuePath)
    return {
      post_id: string(item.post_id, `${valuePath}.post_id`),
      bookmark: boolean(item.bookmark, `${valuePath}.bookmark`),
    }
  })
}

export async function joinExploreGroup(
  id: string,
  signal?: AbortSignal,
): Promise<DirectJoinResult> {
  const response = await client.post<ApiResponse<unknown>>(
    API_PATHS.explore.directJoin.replace(':id', id),
    undefined,
    { signal },
  )
  return decodeEnvelope(response.data, (value, path) => {
    const item = record(value, path)
    return {
      ...decodeGroup(item, path),
      team_id: string(item.team_id, `${path}.team_id`),
      member_id: string(item.member_id, `${path}.member_id`),
    }
  })
}

export async function listRelatedGroups(
  topicId: string,
  params: RelatedGroupListParams = {},
  signal?: AbortSignal,
): Promise<ExplorePage<ExploreGroupCard>> {
  const query = Object.fromEntries(Object.entries({
    purpose: params.purpose,
    page: params.page,
    page_size: params.pageSize,
  }).filter(([, value]) => value !== undefined))
  const response = await client.get<ApiResponse<unknown>>(
    API_PATHS.explore.relatedGroups.replace(':id', topicId),
    { params: query, signal },
  )
  return decodeEnvelope(response.data, decodePage(decodeGroup, 20))
}
