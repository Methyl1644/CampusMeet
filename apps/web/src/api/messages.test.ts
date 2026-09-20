import { beforeEach, describe, expect, it, vi } from 'vitest'
import { get } from './client'
import { getConversation, getConversations, getMessages } from './messages'

vi.mock('./client', () => ({ get: vi.fn(), post: vi.fn() }))

describe('messages api', () => {
  beforeEach(() => vi.clearAllMocks())

  it('loads one conversation without refetching the whole inbox', async () => {
    vi.mocked(get).mockResolvedValue({ id: 'conversation-9' })

    await expect(getConversation('conversation-9')).resolves.toEqual({ id: 'conversation-9' })
    expect(get).toHaveBeenCalledWith('/api/messages/conversations/conversation-9')
  })

  it('unwraps paginated conversations and messages', async () => {
    vi.mocked(get)
      .mockResolvedValueOnce({ list: [{ id: '1' }], total: 1, page: 1, page_size: 20, pages: 1 })
      .mockResolvedValueOnce({ list: [{ id: '2' }], total: 1, page: 1, page_size: 50, pages: 1 })

    await expect(getConversations()).resolves.toEqual([{ id: '1' }])
    await expect(getMessages('1', { latest: true, page_size: 30 })).resolves.toEqual({
      list: [{ id: '2' }], total: 1, page: 1, page_size: 50, pages: 1,
    })
    expect(get).toHaveBeenLastCalledWith(expect.any(String), { latest: true, page_size: 30 })
  })
})
