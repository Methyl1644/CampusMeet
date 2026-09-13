// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import type { User } from '@shared/types'
import Management from './Management'
import { useAuthStore } from '@/store/authStore'
import {
  getOrganizationApplications,
  getPlatformRoles,
  getTopicCollaborators,
  invitePlatformRole,
} from '@/api/management'

vi.mock('@/api/management', () => ({
  getManagementPermissions: vi.fn(),
  getPlatformRoles: vi.fn(),
  invitePlatformRole: vi.fn(),
  suspendPlatformRole: vi.fn(),
  revokePlatformRole: vi.fn(),
  getOrganizationApplications: vi.fn(),
  reviewOrganizationApplication: vi.fn(),
  getManagedOrganizations: vi.fn(),
  getOrganizationMembers: vi.fn(),
  inviteOrganizationMember: vi.fn(),
  revokeOrganizationMember: vi.fn(),
  transferOrganizationOwnership: vi.fn(),
  getTopicCollaborators: vi.fn(),
  inviteTopicCollaborator: vi.fn(),
  revokeTopicCollaborator: vi.fn(),
}))

const baseUser: User = {
  id: '1',
  nickname: '管理者',
  auth_status: 'campus_verified',
  email: 'manager@smail.nju.edu.cn',
  skills: [],
  onboarding_step: 4,
  onboarding_completed: true,
  interests: [],
  looking_for: [],
  availability: {},
  profile_visibility: {
    major: true,
    grade: true,
    interests: true,
    skills: true,
    availability: true,
    contact: false,
  },
}

const emptyPage = { list: [], total: 0, page: 1, page_size: 20, pages: 0 }

function renderPage() {
  return render(<MemoryRouter><Management /></MemoryRouter>)
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(getPlatformRoles).mockResolvedValue(emptyPage)
  vi.mocked(getOrganizationApplications).mockResolvedValue(emptyPage)
  vi.mocked(getTopicCollaborators).mockResolvedValue(emptyPage)
})

afterEach(() => {
  cleanup()
  useAuthStore.getState().logout()
})

describe('management center', () => {
  it('blocks ordinary allowlisted users from management controls', () => {
    useAuthStore.getState().setAuth('token', {
      ...baseUser,
      identity: {
        campus_verified: true,
        platform_role: null,
        organization_roles: [],
        topic_roles: [],
        post_roles: [],
      },
    })

    renderPage()

    expect(screen.getByRole('heading', { name: '暂无管理权限' })).not.toBeNull()
    expect(screen.queryByRole('button', { name: '平台角色' })).toBeNull()
  })

  it('shows only operator sections and invites a platform operator', async () => {
    useAuthStore.getState().setAuth('token', {
      ...baseUser,
      identity: {
        campus_verified: true,
        platform_role: 'senior_operator',
        organization_roles: [],
        topic_roles: [],
        post_roles: [],
      },
    })
    vi.mocked(invitePlatformRole).mockResolvedValue({
      grant_id: '8', user_id: '22', role: 'operator', status: 'active', granted_by: '1',
    })

    renderPage()

    expect(await screen.findByRole('button', { name: '平台角色' })).not.toBeNull()
    expect(screen.getByRole('button', { name: '组织审核' })).not.toBeNull()
    expect(screen.queryByRole('button', { name: '组织成员' })).toBeNull()
    fireEvent.change(screen.getByLabelText('用户 ID'), { target: { value: '22' } })
    fireEvent.click(screen.getByRole('button', { name: '发送角色邀请' }))

    await waitFor(() => expect(invitePlatformRole).toHaveBeenCalledWith({
      user_id: 22,
      role: 'operator',
    }))
  })
})
