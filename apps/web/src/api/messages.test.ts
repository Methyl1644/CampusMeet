import { beforeEach, describe, expect, it, vi } from 'vitest'
import { get } from './client'
import { getConversations, getMessages } from './messages'

vi.mock('./client', () => ({ get: vi.fn(), post: vi.fn() }))

describe('messages api', () => {
  beforeEach(() => vi.clearAllMocks())

  it('unwraps paginated conversations and messages', async () => {
    vi.mocked(get)
      .mockResolvedValueOnce({ list: [{ id: '1' }], total: 1, page: 1, page_size: 20, pages: 1 })
      .mockResolvedValueOnce({ list: [{ id: '2' }], total: 1, page: 1, page_size: 50, pages: 1 })

    await expect(getConversations()).resolves.toEqual([{ id: '1' }])
    await expect(getMessages('1')).resolves.toEqual([{ id: '2' }])
  })
})
