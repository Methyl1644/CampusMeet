// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import type { User } from '@shared/types'
import Authorizations from './Authorizations'
import { useAuthStore } from '@/store/authStore'
import { getProfile } from '@/api/auth'
import {
  acceptPlatformRole,
  declineOrganizationInvitation,
  getMyOrganizationApplications,
  getMyOrganizationInvitations,
  getMyOwnershipTransfers,
  getMyPlatformRoles,
  getMyPostCollaborations,
  getMyTopicCollaborations,
} from '@/api/authorizations'

vi.mock('@/api/auth', () => ({ getProfile: vi.fn() }))
vi.mock('@/api/authorizations', () => ({
  getMyPlatformRoles: vi.fn(),
  acceptPlatformRole: vi.fn(),
  declinePlatformRole: vi.fn(),
  getMyOrganizationInvitations: vi.fn(),
  acceptOrganizationInvitation: vi.fn(),
  declineOrganizationInvitation: vi.fn(),
  getMyTopicCollaborations: vi.fn(),
  acceptTopicCollaboration: vi.fn(),
  declineTopicCollaboration: vi.fn(),
  getMyPostCollaborations: vi.fn(),
  acceptPostCollaboration: vi.fn(),
  declinePostCollaboration: vi.fn(),
  getMyOwnershipTransfers: vi.fn(),
  acceptOwnershipTransfer: vi.fn(),
  declineOwnershipTransfer: vi.fn(),
  getMyOrganizationApplications: vi.fn(),
  submitOrganizationApplication: vi.fn(),
}))

const user: User = {
  id: '2', nickname: '受邀者', email: 'invitee@smail.nju.edu.cn', auth_status: 'campus_verified',
  skills: [], onboarding_step: 4, onboarding_completed: true, interests: [], looking_for: [], availability: {},
  profile_visibility: { major: true, grade: true, interests: true, skills: true, availability: true, contact: false },
}
const emptyPage = { list: [], total: 0, page: 1, page_size: 20, pages: 0 }

beforeEach(() => {
  vi.clearAllMocks()
  useAuthStore.getState().setAuth('token', user)
  vi.mocked(getMyPlatformRoles).mockResolvedValue({ ...emptyPage, list: [{ grant_id: '10', user_id: '2', role: 'operator', status: 'pending', granted_by: '1' }] })
  vi.mocked(getMyOrganizationInvitations).mockResolvedValue({ ...emptyPage, list: [{ invitation_id: '20', organization_id: '3', organization_name: '校科协', inviter_id: '1', invitee_id: '2', role: 'publisher', status: 'pending', expires_at: '2026-10-01T00:00:00Z' }] })
  vi.mocked(getMyTopicCollaborations).mockResolvedValue(emptyPage)
  vi.mocked(getMyPostCollaborations).mockResolvedValue(emptyPage)
  vi.mocked(getMyOwnershipTransfers).mockResolvedValue(emptyPage)
  vi.mocked(getMyOrganizationApplications).mockResolvedValue(emptyPage)
  vi.mocked(getProfile).mockResolvedValue({ ...user, identity: { campus_verified: true, platform_role: 'operator', organization_roles: [], topic_roles: [], post_roles: [] } })
})

afterEach(() => {
  cleanup()
  useAuthStore.getState().logout()
})

describe('authorization inbox', () => {
  it('accepts a platform role after password confirmation and refreshes identity', async () => {
    render(<MemoryRouter><Authorizations /></MemoryRouter>)
    await screen.findByText('平台运营')

    fireEvent.change(screen.getByLabelText('当前密码'), { target: { value: 'Password2026' } })
    fireEvent.click(screen.getByRole('button', { name: '接受平台角色' }))

    await waitFor(() => expect(acceptPlatformRole).toHaveBeenCalledWith('10', 'Password2026'))
    await waitFor(() => expect(useAuthStore.getState().user?.identity?.platform_role).toBe('operator'))
  })

  it('lets the recipient decline an official publisher invitation', async () => {
    render(<MemoryRouter><Authorizations /></MemoryRouter>)
    await screen.findByText('校科协')

    fireEvent.click(screen.getByRole('button', { name: '拒绝组织邀请' }))

    await waitFor(() => expect(declineOrganizationInvitation).toHaveBeenCalledWith('20'))
  })
})
