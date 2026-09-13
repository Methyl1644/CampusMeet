import { beforeEach, describe, expect, it, vi } from 'vitest'
import { API_PATHS } from '@shared/constants'
import { get } from './client'
import { getMyTeams } from './teams'
import { teamFixture } from '@/pages/detailTestFixtures'

vi.mock('./client', () => ({
  get: vi.fn(),
  patch: vi.fn(),
}))

beforeEach(() => vi.resetAllMocks())

describe('teams client', () => {
  it('returns the real paginated my-teams payload and sends bounded paging inputs', async () => {
    const response = {
      list: [teamFixture],
      total: 101,
      page: 2,
      page_size: 100,
      pages: 2,
    }
    vi.mocked(get).mockResolvedValue(response)
    const controller = new AbortController()

    const result = await getMyTeams({ page: 2, page_size: 100 }, controller.signal)

    expect(result).toEqual(response)
    expect(get).toHaveBeenCalledWith(
      API_PATHS.teams.myTeams,
      { page: 2, page_size: 100 },
      controller.signal,
    )
  })
})
