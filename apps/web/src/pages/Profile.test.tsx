// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes, useParams } from 'react-router-dom'
import { getProfile } from '@/api/auth'
import { getMyPosts } from '@/api/posts'
import { getMyApplications } from '@/api/applications'
import { getMyTeams } from '@/api/teams'
import { ToastProvider } from '@/components/Toast'
import Profile from './Profile'
import { viewerFixture } from './detailTestFixtures'

vi.mock('@/api/auth', () => ({ getProfile: vi.fn(), updateProfile: vi.fn() }))
vi.mock('@/api/posts', () => ({ getMyPosts: vi.fn() }))
vi.mock('@/api/applications', () => ({ getMyApplications: vi.fn() }))
vi.mock('@/api/teams', () => ({ getMyTeams: vi.fn() }))
vi.mock('@/store/authStore', () => ({
  useAuthStore: () => ({ user: null, logout: vi.fn(), updateUser: vi.fn() }),
}))

function TeamDestination() {
  const { id } = useParams()
  return <h1>团队目的地 {id}</h1>
}

function summary(index: number) {
  return {
    id: `team-${index}`,
    post_id: `post-${index}`,
    activity_name: `第 ${index} 个团队`,
    my_role: index === 21 ? '交互设计' : null,
    created_at: `2026-09-${String(Math.min(index, 30)).padStart(2, '0')}T08:00:00+08:00`,
  }
}

function renderProfile() {
  return render(
    <MemoryRouter initialEntries={['/profile']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <ToastProvider>
        <Routes>
          <Route path="/profile" element={<Profile />} />
          <Route path="/teams/:id" element={<TeamDestination />} />
        </Routes>
      </ToastProvider>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(getProfile).mockResolvedValue(viewerFixture)
  vi.mocked(getMyPosts).mockResolvedValue([])
  vi.mocked(getMyApplications).mockResolvedValue({
    list: [], total: 0, page: 1, page_size: 20, pages: 0,
  })
  vi.mocked(getMyTeams)
    .mockResolvedValueOnce({
      list: Array.from({ length: 20 }, (_, index) => summary(index + 1)),
      total: 21,
      page: 1,
      page_size: 20,
      pages: 2,
    })
    .mockResolvedValueOnce({
      list: [summary(21)],
      total: 21,
      page: 2,
      page_size: 20,
      pages: 2,
    })
})

afterEach(() => cleanup())

describe('Profile team summaries', () => {
  it('shows the server total, loads later summary pages, and navigates to the selected team', async () => {
    renderProfile()

    expect(await screen.findByRole('heading', { name: viewerFixture.nickname })).toBeTruthy()
    expect(getMyTeams).toHaveBeenNthCalledWith(1, { page: 1, page_size: 20 })
    expect(screen.getByText('21', { selector: 'span' })).toBeTruthy()

    fireEvent.click(screen.getByRole('tab', { name: '我的团队' }))
    const panel = screen.getByRole('tabpanel')
    expect(within(panel).getByText('已显示 20 / 共 21 个团队')).toBeTruthy()

    fireEvent.click(within(panel).getByRole('button', { name: '加载更多团队' }))
    const destination = await within(panel).findByRole('button', { name: /第 21 个团队/ })
    expect(destination.textContent).toContain('我的角色：交互设计')
    await waitFor(() => expect(getMyTeams).toHaveBeenNthCalledWith(2, { page: 2, page_size: 20 }))

    fireEvent.click(destination)
    expect(await screen.findByRole('heading', { name: '团队目的地 team-21' })).toBeTruthy()
  })
})
