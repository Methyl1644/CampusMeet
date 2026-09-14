// @vitest-environment jsdom

import { render, screen } from '@testing-library/react'
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
    vi.mocked(acceptApplication).mockResolvedValue({ accepted: true })
    vi.mocked(rejectApplication).mockResolvedValue({ rejected: true })
  })

  it('renders applications from the paginated response and exposes admission', async () => {
    vi.mocked(getPostApplications).mockResolvedValue({
      list: [{
        id: '12', post_id: '3',
        applicant: { id: '2', nickname: '申请者', auth_status: 'verified' },
        role_wanted: '前端', experience: '有项目经验', available_time: '周末',
        reason: '希望加入', status: 'pending', created_at: '2026-09-14T08:00:00Z',
      }],
      total: 1, page: 1, page_size: 20, pages: 1,
    })

    render(<PostApplicationsPanel postId="3" />)

    expect(await screen.findByText(/申请者/)).toBeTruthy()
    expect(screen.getByRole('button', { name: '接受并加入小组' })).toBeTruthy()
  })
})
