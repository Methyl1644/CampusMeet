import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./client', () => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
}))

import { get, post } from './client'
import { getQuickExperienceStatus, quickExperience } from './auth'
import { API_PATHS } from '@shared/constants'

describe('quick experience API', () => {
  beforeEach(() => vi.clearAllMocks())

  it('loads availability without credentials', async () => {
    await getQuickExperienceStatus()
    expect(get).toHaveBeenCalledWith(API_PATHS.auth.quickExperienceStatus)
  })

  it('requests a temporary reviewer session', async () => {
    await quickExperience()
    expect(post).toHaveBeenCalledWith(API_PATHS.auth.quickExperience)
  })
})
