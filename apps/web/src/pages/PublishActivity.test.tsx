// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import PublishActivity from './PublishActivity'
import { getTags } from '@/api/content'
import { useAuthStore } from '@/store/authStore'
import type { User } from '@shared/types'
import { uploadTopicCover } from '@/api/publish'

vi.mock('@/api/content', () => ({ getTags: vi.fn(), createTopic: vi.fn() }))
vi.mock('@/api/publish', () => ({ attachPublicUpload: vi.fn(), uploadTopicCover: vi.fn() }))

const user: User = {
  id: '4', nickname: '工作人员', email: 'staff@smail.nju.edu.cn', auth_status: 'campus_verified',
  skills: [], onboarding_step: 4, onboarding_completed: true, interests: [], looking_for: [], availability: {},
  profile_visibility: { major: true, grade: true, interests: true, skills: true, availability: true, contact: false },
}

describe('formal activity publishing', () => {
  beforeEach(() => {
    vi.mocked(getTags).mockResolvedValue([])
    vi.mocked(uploadTopicCover).mockResolvedValue('topic-cover-upload')
  })
  afterEach(() => { cleanup(); useAuthStore.getState().logout(); vi.clearAllMocks() })

  it('opens for configured staff', async () => {
    useAuthStore.getState().setAuth('token', { ...user, identity: { campus_verified: true, is_staff: true, platform_role: 'senior_operator', organization_roles: [], topic_roles: [], post_roles: [] } })
    render(<MemoryRouter><PublishActivity /></MemoryRouter>)
    expect(await screen.findByRole('heading', { name: '发布正式活动' })).not.toBeNull()
    const campus = screen.getByLabelText('校区')
    expect(campus.tagName).toBe('SELECT')
    expect(screen.getAllByRole('option').map((option) => option.textContent)).toEqual(expect.arrayContaining(['鼓楼校区', '仙林校区', '苏州校区', '浦口校区']))
    const file = new File(['cover'], 'activity.png', { type: 'image/png' })
    fireEvent.change(screen.getByLabelText('上传活动封面'), { target: { files: [file] } })
    await waitFor(() => expect(uploadTopicCover).toHaveBeenCalledWith(file))
  })

  it('remains unavailable to an ordinary user', () => {
    useAuthStore.getState().setAuth('token', { ...user, identity: { campus_verified: true, platform_role: null, organization_roles: [], topic_roles: [], post_roles: [] } })
    render(<MemoryRouter><PublishActivity /></MemoryRouter>)
    expect(screen.getByRole('heading', { name: '暂无正式活动发布权限' })).not.toBeNull()
  })
})
