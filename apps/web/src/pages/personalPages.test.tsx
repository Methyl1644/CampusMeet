// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { ToastProvider } from '@/components/Toast'
import { getMyActivities, getMyGroups, getPersonalSettings, getPublicProfile, updatePersonalProfile, updatePersonalSettings } from '@/api/personal'
import { getNotifications, markNotificationRead } from '@/api/notifications'
import MyActivities from './MyActivities'
import MyGroups from './MyGroups'
import Notifications from './Notifications'
import PublicProfile from './PublicProfile'
import Settings from './Settings'

vi.mock('@/api/personal', () => ({
  getMyActivities: vi.fn(), getMyGroups: vi.fn(), getPersonalSettings: vi.fn(),
  getPublicProfile: vi.fn(), updatePersonalProfile: vi.fn(), updatePersonalSettings: vi.fn(),
}))
vi.mock('@/api/notifications', () => ({ getNotifications: vi.fn(), markNotificationRead: vi.fn(), markAllNotificationsRead: vi.fn() }))
vi.mock('@/api/explore', () => ({ setActivityFavorite: vi.fn(), setGroupFavorite: vi.fn() }))
vi.mock('@/api/auth', () => ({ changePassword: vi.fn(), deactivateAccount: vi.fn() }))
vi.mock('@/features/home/HomeFeedContext', () => ({ useHomeFeed: () => ({ setNotificationUnread: vi.fn() }) }))

const emptyPage = { list: [], total: 0, page: 1, page_size: 20, pages: 0 }
const settings = {
  nickname: '小紫', avatar: null, bio: '', major: '软件学院', grade: '2024级', interests: [], looking_for: [], skills: [], availability: {},
  profile_visibility: { major: true, grade: true, interests: true, skills: true, availability: false, contact: false },
  notification_preferences: { applications: true, teams: true, moderation: true, deadlines: true, messages: true },
}

function renderAt(path: string, element: React.ReactNode, routePath = '*') {
  return render(<MemoryRouter initialEntries={[path]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><ToastProvider><Routes><Route path={routePath} element={element} /></Routes></ToastProvider></MemoryRouter>)
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(getMyActivities).mockResolvedValue(emptyPage)
  vi.mocked(getMyGroups).mockResolvedValue(emptyPage)
  vi.mocked(getPersonalSettings).mockResolvedValue(settings)
  vi.mocked(getNotifications).mockResolvedValue(emptyPage)
})
afterEach(() => cleanup())

describe('personal area pages', () => {
  it('honors activity and group collection views from the URL', async () => {
    const activity = renderAt('/my/activities?view=saved', <MyActivities />)
    await waitFor(() => expect(getMyActivities).toHaveBeenCalledWith('saved', 1, 20))
    expect(screen.getByRole('tab', { name: '已收藏' }).getAttribute('aria-selected')).toBe('true')
    activity.unmount()
    renderAt('/my/groups?view=archived', <MyGroups />)
    await waitFor(() => expect(getMyGroups).toHaveBeenCalledWith('archived', 1, 20))
    expect(screen.getByRole('tab', { name: '已归档' }).getAttribute('aria-selected')).toBe('true')
  })

  it('marks unknown-target notifications read without creating an unsafe link', async () => {
    vi.mocked(getNotifications).mockResolvedValue({ ...emptyPage, total: 1, pages: 1, list: [{ id: 'n1', event_type: 'system', title: '审核完成', body: '内容已通过', target_type: 'external', target_id: 'javascript:alert(1)', read_at: null, created_at: '2026-09-13T08:00:00Z' }] })
    vi.mocked(markNotificationRead).mockResolvedValue({ id: 'n1', event_type: 'system', title: '审核完成', body: '内容已通过', read_at: '2026-09-13T08:01:00Z', created_at: '2026-09-13T08:00:00Z', unread_count: 0 })
    renderAt('/notifications', <Notifications />)
    const item = await screen.findByRole('button', { name: /审核完成/ })
    fireEvent.click(item)
    await waitFor(() => expect(markNotificationRead).toHaveBeenCalledWith('n1'))
    expect(screen.queryByRole('link')).toBeNull()
  })

  it('renders only fields returned by the public profile projection', async () => {
    vi.mocked(getPublicProfile).mockResolvedValue({ id: '8', nickname: '林晓', avatar: null, bio: null, looking_for: [], activities: [], groups: [], is_owner: false })
    renderAt('/users/8', <PublicProfile />, '/users/:id')
    expect(await screen.findByRole('heading', { name: '林晓' })).toBeTruthy()
    expect(screen.queryByText(/联系方式/)).toBeNull()
  })

  it('keeps edited settings after a failed save', async () => {
    vi.mocked(updatePersonalSettings).mockRejectedValue(new Error('offline'))
    vi.mocked(updatePersonalProfile).mockResolvedValue(settings)
    renderAt('/settings', <Settings />)
    const nickname = await screen.findByLabelText('昵称')
    fireEvent.change(nickname, { target: { value: '保留的草稿' } })
    fireEvent.click(screen.getByRole('button', { name: '保存设置' }))
    await waitFor(() => expect(updatePersonalSettings).toHaveBeenCalled())
    expect((nickname as HTMLInputElement).value).toBe('保留的草稿')
  })
})
