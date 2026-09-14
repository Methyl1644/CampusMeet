import { get, patch, post } from './client'
import { API_PATHS } from '@shared/constants'
import type {
  PaginatedResponse,
  Post,
  SearchDirectResult,
  StandardTag,
  Topic,
} from '@shared/types'

export function getTopics(params: {
  channel?: 'official' | 'organization'
  q?: string
  tag_ids?: string[]
  page?: number
  page_size?: number
}) {
  return get<PaginatedResponse<Topic>>(API_PATHS.content.topics, {
    ...params,
    tag_ids: params.tag_ids?.join(','),
  })
}

export function getTopic(id: string) {
  return get<Topic>(API_PATHS.content.topicDetail.replace(':id', id))
}

export function getTopicPosts(id: string) {
  return get<Post[]>(API_PATHS.content.topicPosts.replace(':id', id))
}

export function toggleTopicFollow(id: string) {
  return post<{ followed: boolean; follower_count: number }>(
    API_PATHS.content.topicFollow.replace(':id', id),
  )
}

export function getSearchSuggestions(q: string, channel: string) {
  return get<{ direct: SearchDirectResult[]; tags: StandardTag[] }>(
    API_PATHS.content.searchSuggestions,
    { q, channel },
  )
}

export function getTags() {
  return get<StandardTag[]>(API_PATHS.content.tags)
}

export interface TopicCreateInput {
  channel: 'official' | 'organization'
  title: string
  short_title: string
  organizer: string
  organizer_key: string
  canonical_event_key: string
  edition: string
  summary: string
  content: string
  source_url?: string
  cover_url?: string
  registration_deadline?: string | null
  activity_start_at?: string | null
  activity_end_at?: string | null
  location_name?: string
  campus_scope?: string
  capacity?: number | null
  participation_mode: 'open_team' | 'official_signup' | 'information_only'
  organization_id?: number | null
  tag_ids: string[]
}

export function createTopic(body: TopicCreateInput) {
  return post<Topic>(API_PATHS.content.topics, body)
}

export type TopicUpdateInput = Partial<Omit<TopicCreateInput, 'channel' | 'organization_id'>>

export function updateTopic(id: string, body: TopicUpdateInput) {
  return patch<Topic>(API_PATHS.content.topicDetail.replace(':id', id), body)
}
