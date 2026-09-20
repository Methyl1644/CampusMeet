// @vitest-environment jsdom

import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { acceptApplication, getPostApplications, rejectApplication } from '@/api/applications'
import PostApplicationsPanel from './PostApplicationsPanel'

vi.mock('@/api/applications', () => ({
  acceptApplication: vi.fn(),
  getPostApplications: vi.fn(),
  rejectApplication: vi.fn(),
}))

describe('PostApplicationsPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(acceptApplication).mockResolvedValue({ accepted: true, conversation_id: 'conversation-9' })
    vi.mocked(rejectApplication).mockResolvedValue({ rejected: true })
  })

  it('renders applications from the paginated response and exposes admission', async () => {
    vi.mocked(getPostApplications).mockResolvedValue({
      list: [{
        id: '12', post_id: '3',
        applicant: { id: '2', nickname: '申请者', auth_status: 'verified', major: '软件工程', grade: '大二' },
        role_wanted: '前端', experience: '有项目经验', available_time: '周末',
        reason: '希望加入', questions: ['什么时候开会？'], status: 'pending', created_at: '2026-09-14T08:00:00Z',
      }],
      total: 1, page: 1, page_size: 20, pages: 1,
    })

    render(
      <MemoryRouter initialEntries={['/posts/3']}>
        <Routes>
          <Route path="/posts/:id" element={<PostApplicationsPanel postId="3" />} />
          <Route path="/messages/:conversationId" element={<div>临时会话已打开</div>} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByText(/申请者/)).toBeTruthy()
    expect(screen.getByText(/可投入时间：周末/)).toBeTruthy()
    expect(screen.getByText(/什么时候开会/)).toBeTruthy()
    expect(screen.getByRole('link', { name: /查看申请者公开资料/ }).getAttribute('href')).toBe('/users/2')

    fireEvent.click(screen.getByRole('button', { name: '同意并开启临时会话' }))
    await waitFor(() => expect(screen.getByText('临时会话已打开')).toBeTruthy())
  })
})
