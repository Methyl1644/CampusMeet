import { beforeEach, describe, expect, it, vi } from 'vitest'
import { API_PATHS } from '@shared/constants'
import { client } from './client'
import {
  getManagedOrganizations,
  getManagementPermissions,
  getOrganizationApplications,
  getOrganizationMembers,
  getPlatformRoles,
  getTopicCollaborators,
  inviteOrganizationMember,
  invitePlatformRole,
  inviteTopicCollaborator,
  reviewOrganizationApplication,
  revokeOrganizationMember,
  revokePlatformRole,
  revokeTopicCollaborator,
  suspendPlatformRole,
  transferOrganizationOwnership,
} from './management'

vi.mock('./client', () => ({
  client: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}))

const ok = (data: unknown) => ({ data: { code: 0, message: 'ok', data } })

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(client.get).mockResolvedValue(ok({ list: [], total: 0, page: 1, page_size: 20, pages: 0 }))
  vi.mocked(client.post).mockResolvedValue(ok({}))
  vi.mocked(client.delete).mockResolvedValue(ok({}))
})

describe('management API contracts', () => {
  it('loads permissions, roles, reviews, organizations, members, and collaborators', async () => {
    await getManagementPermissions()
    await getPlatformRoles()
    await getOrganizationApplications()
    await getManagedOrganizations()
    await getOrganizationMembers('4')
    await getTopicCollaborators('8')

    expect(client.get).toHaveBeenNthCalledWith(1, API_PATHS.content.permissions)
    expect(client.get).toHaveBeenNthCalledWith(2, API_PATHS.operators.roles, { params: { status: 'all' } })
    expect(client.get).toHaveBeenNthCalledWith(3, API_PATHS.identity.applicationQueue, { params: { status: 'pending' } })
    expect(client.get).toHaveBeenNthCalledWith(4, API_PATHS.identity.managedOrganizations)
    expect(client.get).toHaveBeenNthCalledWith(5, '/api/organizations/4/members')
    expect(client.get).toHaveBeenNthCalledWith(6, '/api/topics/8/collaborators')
  })

  it('uses exact mutation routes and bodies', async () => {
    await invitePlatformRole({ user_id: 2, role: 'operator' })
    await suspendPlatformRole('11', '轮换')
    await revokePlatformRole('12', '离任')
    await reviewOrganizationApplication('20', { decision: 'approve', reason: '', validity_days: 365 })
    await inviteOrganizationMember('4', { user_id: 3, role: 'publisher' })
    await revokeOrganizationMember('4', '3')
    await transferOrganizationOwnership('4', '3')
    await inviteTopicCollaborator('8', { user_id: 5, role: 'manager' })
    await revokeTopicCollaborator('8', '5')

    expect(client.post).toHaveBeenNthCalledWith(1, API_PATHS.operators.invitations, { user_id: 2, role: 'operator' })
    expect(client.post).toHaveBeenNthCalledWith(2, '/api/operators/roles/11/suspend', { reason: '轮换' })
    expect(client.post).toHaveBeenNthCalledWith(3, '/api/operators/roles/12/revoke', { reason: '离任' })
    expect(client.post).toHaveBeenNthCalledWith(4, '/api/operators/organization-applications/20/review', { decision: 'approve', reason: '', validity_days: 365 })
    expect(client.post).toHaveBeenNthCalledWith(5, '/api/organizations/4/invitations', { user_id: 3, role: 'publisher' })
    expect(client.delete).toHaveBeenNthCalledWith(1, '/api/organizations/4/members/3')
    expect(client.post).toHaveBeenNthCalledWith(6, '/api/organizations/4/ownership-transfers', { target_user_id: 3 })
    expect(client.post).toHaveBeenNthCalledWith(7, '/api/topics/8/collaborators', { user_id: 5, role: 'manager' })
    expect(client.delete).toHaveBeenNthCalledWith(2, '/api/topics/8/collaborators/5')
  })
})
