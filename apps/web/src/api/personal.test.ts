import { beforeEach, describe, expect, it, vi } from 'vitest'
import { API_PATHS } from '@shared/constants'
import { get, patch } from './client'
import {
  getMyActivities,
  getMyGroups,
  getPersonalSettings,
  getPublicProfile,
  updatePersonalSettings,
  updatePersonalProfile,
} from './personal'

vi.mock('./client', () => ({ get: vi.fn(), patch: vi.fn() }))

beforeEach(() => vi.clearAllMocks())

describe('personal area client', () => {
  it('uses bounded canonical collection routes', async () => {
    vi.mocked(get).mockResolvedValue({ list: [], total: 0, page: 1, page_size: 40, pages: 0 })
    await getMyActivities('saved', 2, 99)
    await getMyGroups('pending', 3, 99)
    expect(get).toHaveBeenNthCalledWith(1, API_PATHS.personal.activities, { view: 'saved', page: 2, page_size: 40 })
    expect(get).toHaveBeenNthCalledWith(2, API_PATHS.personal.groups, { view: 'pending', page: 3, page_size: 40 })
  })

  it('loads public profiles and settings and preserves explicit patches', async () => {
    vi.mocked(get).mockResolvedValue({})
    vi.mocked(patch).mockResolvedValue({})
    await getPublicProfile('18')
    await getPersonalSettings()
    await updatePersonalProfile({ nickname: 'Lin' })
    await updatePersonalSettings({ notification_preferences: { messages: false } })
    expect(get).toHaveBeenNthCalledWith(1, API_PATHS.personal.publicProfile.replace(':id', '18'))
    expect(get).toHaveBeenNthCalledWith(2, API_PATHS.personal.settings)
    expect(patch).toHaveBeenNthCalledWith(1, API_PATHS.personal.profile, { nickname: 'Lin' })
    expect(patch).toHaveBeenNthCalledWith(2, API_PATHS.personal.settings, { notification_preferences: { messages: false } })
  })
})
