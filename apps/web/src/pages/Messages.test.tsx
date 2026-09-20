// @vitest-environment jsdom

import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { closeConversation, confirmTeam, getConversation, getConversations, getMessages, sendMessage } from '@/api/messages'
import { ToastProvider } from '@/components/Toast'
import Messages from './Messages'
import type { Conversation, PaginatedResponse, Message } from '@shared/types'

vi.mock('@/api/messages', () => ({
  closeConversation: vi.fn(),
  confirmTeam: vi.fn(),
  getConversation: vi.fn(),
  getConversations: vi.fn(),
  getMessages: vi.fn(),
  sendMessage: vi.fn(),
}))

const conversation: Conversation = {
  id: 'conversation-1', post_id: 'post-1', post_title: '玄武湖同行',
  other_user: { id: 'user-2', nickname: '林同学', auth_status: 'campus_verified' },
  last_message: '你好', last_message_at: '2026-09-20T10:00:00+08:00', unread_count: 1,
  status: 'active', contact_unlocked: false, my_confirmed: false,
}

const firstPage: PaginatedResponse<Message> = {
  list: [{
    id: 'message-1', conversation_id: conversation.id, sender_id: 'user-2',
    content: '你好', created_at: '2026-09-20T10:00:00+08:00', is_mine: false,
  }],
  total: 1, page: 1, page_size: 30, pages: 1,
}

function renderMessages() {
  return render(
    <MemoryRouter initialEntries={['/messages/conversation-1']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <ToastProvider>
        <Routes>
          <Route path="/messages/:conversationId" element={<Messages />} />
          <Route path="/teams/:teamId" element={<div>团队详情</div>} />
        </Routes>
      </ToastProvider>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(getConversations).mockResolvedValue([conversation])
  vi.mocked(getConversation).mockResolvedValue(conversation)
  vi.mocked(getMessages).mockResolvedValue(firstPage)
  vi.mocked(closeConversation).mockResolvedValue({ closed: true })
  vi.mocked(sendMessage).mockResolvedValue(firstPage.list[0])
})

afterEach(() => cleanup())

describe('Messages', () => {
  it('loads the latest message page when a conversation opens', async () => {
    renderMessages()
    expect(await screen.findByText('你好')).toBeTruthy()
    expect(getMessages).toHaveBeenCalledWith(conversation.id, { latest: true, page_size: 30 })
  })

  it('keeps chat available after only the current user confirms', async () => {
    vi.mocked(confirmTeam).mockResolvedValue({ confirmed: true, waiting_for_other: true, contact_unlocked: false })
    renderMessages()
    fireEvent.click(await screen.findByRole('button', { name: /愿意组队/ }))

    expect((await screen.findAllByText('已确认，等待对方确认')).length).toBeGreaterThan(0)
    expect(screen.getByLabelText('输入消息')).toBeTruthy()
    expect(screen.queryByRole('button', { name: /愿意组队/ })).toBeNull()
  })

  it('shows the team entry only after both sides confirm', async () => {
    vi.mocked(confirmTeam).mockResolvedValue({
      confirmed: true, waiting_for_other: false, contact_unlocked: true, team_id: 'team-8',
    })
    renderMessages()
    fireEvent.click(await screen.findByRole('button', { name: /愿意组队/ }))

    const link = await screen.findByRole('link', { name: '进入团队空间' })
    expect(link.getAttribute('href')).toBe('/teams/team-8')
    expect(screen.getByLabelText('输入消息')).toBeTruthy()
  })

  it('polls the latest page when an initially empty conversation receives its first message', async () => {
    vi.useFakeTimers()
    vi.mocked(getMessages)
      .mockResolvedValueOnce({ list: [], total: 0, page: 1, page_size: 30, pages: 0 })
      .mockResolvedValueOnce(firstPage)

    renderMessages()
    await act(async () => { await Promise.resolve(); await Promise.resolve() })
    await act(async () => { await vi.advanceTimersByTimeAsync(5000) })

    expect(getMessages).toHaveBeenLastCalledWith(conversation.id, { latest: true, page_size: 30 })
    expect(screen.getAllByText('你好')).toHaveLength(2)
    expect(getConversation).toHaveBeenCalledWith(conversation.id)
    vi.useRealTimers()
  })
})
