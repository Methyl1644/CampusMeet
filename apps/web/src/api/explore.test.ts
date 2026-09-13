import { CanceledError } from 'axios'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { API_PATHS } from '@shared/constants'
import { client } from './client'
import {
  ExploreContractError,
  getExploreActivity,
  getExploreGroup,
  joinExploreGroup,
  listExploreActivities,
  listExploreGroups,
  listRelatedGroups,
  setActivityFavorite,
  setGroupFavorite,
} from './explore'

vi.mock('./client', () => ({
  client: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

const user = {
  id: '8',
  nickname: 'Lin',
  avatar: null,
  major: 'Software Engineering',
  grade: 'Junior',
}

const group = {
  id: '21',
  title: 'Robotics team',
  description: null,
  source_type: 'user',
  kind: 'topic_team',
  purpose: 'team_recruitment',
  join_mode: 'direct',
  topic_id: '10',
  main_category: '竞赛与项目',
  activity_name: 'Robotics challenge',
  cover_url: null,
  cover_placeholder_key: 'category:competition',
  current_members: 2,
  target_members: 4,
  needed_roles: ['Frontend'],
  weekly_hours: '4',
  school_scope: 'Xianlin',
  deadline: '2026-10-01T00:00:00Z',
  risk_level: 'low',
  status: 'recruiting',
  author_id: '8',
  author: user,
  bookmark: false,
  join_state: 'available',
  member_preview: [user],
  linked_activity: {
    id: '10',
    title: 'Robotics challenge',
    short_title: 'Robotics',
    organizer: 'Engineering school',
    cover_url: null,
    cover_placeholder_key: 'activity:organization',
    registration_deadline: '2026-09-25T00:00:00Z',
    activity_start_at: '2026-10-03T00:00:00Z',
    participation_mode: 'open_team',
    status: 'active',
  },
  tags: [{
    tag_id: 'ai',
    canonical_name: 'AI',
    category: 'activity',
    display_color: '#4455aa',
  }],
  collaborators: [],
  created_at: '2026-09-13T00:00:00Z',
}

const activity = {
  id: '10',
  channel: 'organization',
  title: 'Robotics challenge',
  short_title: 'Robotics',
  organizer: 'Engineering school',
  edition: '2026',
  summary: 'Build a robot.',
  content: 'Details',
  source_url: null,
  source_status: 'verified',
  cover_url: null,
  cover_placeholder_key: 'activity:organization',
  location_name: 'Engineering building',
  campus_scope: 'Xianlin',
  capacity: 40,
  registration_deadline: '2026-09-25T00:00:00Z',
  activity_start_at: '2026-10-03T00:00:00Z',
  activity_end_at: null,
  follower_count: 12,
  participant_count: 3,
  participant_preview: [user],
  participation_mode: 'open_team',
  favorite: false,
  followed: false,
  participation_state: 'available',
  tags: group.tags,
  status: 'active',
  trust_badges: [{
    kind: 'verified_organization',
    label: 'Verified organization',
    organization_name: 'Engineering school',
  }],
  responsible_people: [{
    user_id: '8',
    nickname: 'Lin',
    role: 'manager',
    badge: 'Activity manager',
  }],
}

beforeEach(() => {
  vi.resetAllMocks()
})

describe('Explore client decoding and transport', () => {
  it('decodes an activity list and sends tags as one comma-separated query value', async () => {
    vi.mocked(client.get).mockResolvedValue({
      data: { code: 0, message: 'ok', data: {
        list: [activity], total: 1, page: 2, page_size: 20, pages: 1,
      } },
    })

    const result = await listExploreActivities({
      query: 'robot',
      tagIds: ['ai', 'code'],
      date: 'upcoming',
      status: 'registration_open',
      type: 'organization',
      campus: 'Xianlin',
      page: 2,
      pageSize: 20,
    })

    expect(result.list[0].participation_mode).toBe('open_team')
    expect(client.get).toHaveBeenCalledWith(API_PATHS.explore.activities, {
      params: {
        q: 'robot',
        tag_ids: 'ai,code',
        date: 'upcoming',
        status: 'registration_open',
        type: 'organization',
        campus: 'Xianlin',
        page: 2,
        page_size: 20,
      },
      signal: undefined,
    })
  })

  it('rejects a response whose projection violates the approved contract', async () => {
    vi.mocked(client.get).mockResolvedValue({
      data: { code: 0, message: 'ok', data: { ...activity, participation_mode: 'invite_only' } },
    })

    await expect(getExploreActivity('10')).rejects.toBeInstanceOf(ExploreContractError)
  })

  it('decodes group list and detail projections through their distinct endpoints', async () => {
    vi.mocked(client.get)
      .mockResolvedValueOnce({
        data: { code: 0, message: 'ok', data: {
          list: [group], total: 1, page: 1, page_size: 20, pages: 1,
        } },
      })
      .mockResolvedValueOnce({ data: { code: 0, message: 'ok', data: group } })

    await expect(listExploreGroups({ status: 'recruiting' })).resolves.toMatchObject({ total: 1 })
    await expect(getExploreGroup('21')).resolves.toMatchObject({ id: '21', join_mode: 'direct' })

    expect(client.get).toHaveBeenNthCalledWith(1, API_PATHS.explore.groups, {
      params: { status: 'recruiting' },
      signal: undefined,
    })
    expect(client.get).toHaveBeenNthCalledWith(
      2,
      API_PATHS.explore.groupDetail.replace(':id', '21'),
      { signal: undefined },
    )
  })

  it('passes AbortSignal through and propagates request cancellation', async () => {
    const controller = new AbortController()
    vi.mocked(client.get).mockImplementation((_url, config) => new Promise((_resolve, reject) => {
      config?.signal?.addEventListener?.('abort', () => reject(new CanceledError('canceled')))
    }))

    const request = listExploreActivities({}, controller.signal)
    controller.abort()

    await expect(request).rejects.toBeInstanceOf(CanceledError)
  })

  it('uses typed favorite, direct-join, and related-group endpoints', async () => {
    vi.mocked(client.put).mockResolvedValue({
      data: { code: 0, message: 'ok', data: {
        topic_id: '10', favorite: true, followed: true, follower_count: 13,
      } },
    })
    vi.mocked(client.delete).mockResolvedValue({
      data: { code: 0, message: 'ok', data: { post_id: '21', bookmark: false } },
    })
    vi.mocked(client.post).mockResolvedValue({
      data: { code: 0, message: 'ok', data: {
        ...group, join_state: 'joined', team_id: '4', member_id: '9',
      } },
    })
    vi.mocked(client.get).mockResolvedValue({
      data: { code: 0, message: 'ok', data: {
        list: [group], total: 1, page: 1, page_size: 10, pages: 1,
      } },
    })

    await expect(setActivityFavorite('10', true)).resolves.toMatchObject({ favorite: true })
    await expect(setGroupFavorite('21', false)).resolves.toEqual({ post_id: '21', bookmark: false })
    await expect(joinExploreGroup('21')).resolves.toMatchObject({ join_state: 'joined', team_id: '4' })
    await expect(listRelatedGroups('10', {
      purpose: 'discussion', page: 1, pageSize: 10,
    })).resolves.toMatchObject({ total: 1 })

    expect(client.put).toHaveBeenCalledWith(
      API_PATHS.explore.favoriteActivity.replace(':id', '10'),
      undefined,
      { signal: undefined },
    )
    expect(client.delete).toHaveBeenCalledWith(
      API_PATHS.explore.favoriteGroup.replace(':id', '21'),
      { signal: undefined },
    )
    expect(client.post).toHaveBeenCalledWith(
      API_PATHS.explore.directJoin.replace(':id', '21'),
      undefined,
      { signal: undefined },
    )
    expect(client.get).toHaveBeenCalledWith(
      API_PATHS.explore.relatedGroups.replace(':id', '10'),
      { params: { purpose: 'discussion', page: 1, page_size: 10 }, signal: undefined },
    )
  })
})
