import { beforeEach, describe, expect, it, vi } from 'vitest'
import { API_PATHS } from '@shared/constants'
import type { HomeFeed, HomeWarningSection } from '@shared/types'
import { get } from './client'
import { getHomeFeed, homeSectionState } from './home'

vi.mock('./client', () => ({
  get: vi.fn(),
}))

const feed: HomeFeed = {
  profile: {
    id: 'student-1',
    nickname: 'Lin',
    avatar: null,
    major: 'Software Engineering',
    grade: 'Junior',
  },
  deadline_reminder: null,
  recommended_topics: [],
  attending_topics: [],
  followed_topics: [],
  joined_groups: [],
  group_timeline: [],
  unread: {
    messages: 2,
    notifications: 1,
  },
  warnings: ['recommended_topics'],
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('getHomeFeed', () => {
  it('requests the aggregate home endpoint without redundant parameters', async () => {
    vi.mocked(get).mockResolvedValue(feed)

    await expect(getHomeFeed()).resolves.toBe(feed)

    expect(get).toHaveBeenCalledOnce()
    expect(get).toHaveBeenCalledWith(API_PATHS.home.feed)
  })
})

describe('homeSectionState', () => {
  it.each<[HomeWarningSection, 'ready' | 'degraded']>([
    ['recommended_topics', 'degraded'],
    ['followed_topics', 'ready'],
  ])('returns %s warning state as %s', (section, expected) => {
    expect(homeSectionState(feed, section)).toBe(expected)
  })
})
