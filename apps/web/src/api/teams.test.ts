import { beforeEach, describe, expect, expectTypeOf, it, vi } from 'vitest'
import { API_PATHS } from '@shared/constants'
import type { PaginatedResponse } from '@shared/types'
import { get } from './client'
import { getMyTeams } from './teams'

interface ExpectedMyTeamSummary {
  id: string
  post_id: string
  activity_name: string
  my_role: string | null
  created_at: string | null
}

vi.mock('./client', () => ({
  get: vi.fn(),
  patch: vi.fn(),
}))

beforeEach(() => vi.resetAllMocks())

describe('teams client', () => {
  it('returns the real paginated my-teams payload and sends bounded paging inputs', async () => {
    const response = {
      list: [{
        id: 'team-101',
        post_id: 'post-42',
        activity_name: '校园产品创意赛',
        my_role: '交互设计',
        created_at: '2026-09-13T08:00:00+08:00',
      }],
      total: 101,
      page: 2,
      page_size: 100,
      pages: 2,
    }
    vi.mocked(get).mockResolvedValue(response)
    const controller = new AbortController()

    const result = await getMyTeams({ page: 2, page_size: 100 }, controller.signal)

    expect(result).toEqual(response)
    expectTypeOf(result).toEqualTypeOf<PaginatedResponse<ExpectedMyTeamSummary>>()
    expect(get).toHaveBeenCalledWith(
      API_PATHS.teams.myTeams,
      { page: 2, page_size: 100 },
      controller.signal,
    )
  })
})
