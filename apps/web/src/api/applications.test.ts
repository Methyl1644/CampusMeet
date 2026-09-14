// @vitest-environment jsdom

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { client, post } from './client'
import { createApplication } from './applications'

vi.mock('./client', () => ({
  client: { get: vi.fn() },
  get: vi.fn(),
  post: vi.fn(),
}))

describe('applications api', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  it('waits for the backend to become healthy before retrying a network failure', async () => {
    const request = {
      post_id: '3',
      role_wanted: '会踢前锋',
      experience: '1年',
      available_time: '每周2小时',
      reason: '想参加',
    }
    const networkError = Object.assign(new Error('Network Error'), { code: 'ERR_NETWORK' })
    vi.mocked(post)
      .mockRejectedValueOnce(networkError)
      .mockResolvedValueOnce({ id: '12' })
    vi.mocked(client.get)
      .mockRejectedValueOnce(networkError)
      .mockResolvedValueOnce({ data: { status: 'ok' } })

    const result = createApplication(request)
    await vi.advanceTimersByTimeAsync(1500)

    await expect(result).resolves.toEqual({ id: '12' })
    expect(client.get).toHaveBeenCalledTimes(2)
    expect(client.get).toHaveBeenCalledWith('/health', { timeout: 10000 })
    expect(post).toHaveBeenCalledTimes(2)
  })
})
