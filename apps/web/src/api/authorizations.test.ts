import { beforeEach, describe, expect, it, vi } from 'vitest'
import { client } from './client'
import {
  acceptOrganizationInvitation,
  acceptOwnershipTransfer,
  acceptPlatformRole,
  acceptTopicCollaboration,
  declineOrganizationInvitation,
  declineOwnershipTransfer,
  declinePlatformRole,
  declineTopicCollaboration,
  getMyOrganizationInvitations,
  getMyOwnershipTransfers,
  getMyPlatformRoles,
  getMyTopicCollaborations,
} from './authorizations'

vi.mock('./client', () => ({
  client: { get: vi.fn(), post: vi.fn() },
}))

const ok = (data: unknown) => ({ data: { code: 0, message: 'ok', data } })

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(client.get).mockResolvedValue(ok({ list: [], total: 0, page: 1, page_size: 20, pages: 0 }))
  vi.mocked(client.post).mockResolvedValue(ok({}))
})

describe('authorization inbox API contracts', () => {
  it('loads all four invitation sources', async () => {
    await getMyPlatformRoles()
    await getMyOrganizationInvitations()
    await getMyTopicCollaborations()
    await getMyOwnershipTransfers()

    expect(client.get).toHaveBeenNthCalledWith(1, '/api/operators/roles/my', { params: { status: 'pending' } })
    expect(client.get).toHaveBeenNthCalledWith(2, '/api/organizations/invitations/my', { params: { status: 'pending' } })
    expect(client.get).toHaveBeenNthCalledWith(3, '/api/topics/collaborations/my', { params: { status: 'pending' } })
    expect(client.get).toHaveBeenNthCalledWith(4, '/api/organizations/ownership-transfers/my', { params: { status: 'pending' } })
  })

  it('accepts and declines every authorization type', async () => {
    await acceptPlatformRole('1', 'Password2026')
    await declinePlatformRole('1')
    await acceptOrganizationInvitation('2')
    await declineOrganizationInvitation('2')
    await acceptTopicCollaboration('3')
    await declineTopicCollaboration('3')
    await acceptOwnershipTransfer('4')
    await declineOwnershipTransfer('4')

    expect(client.post).toHaveBeenNthCalledWith(1, '/api/operators/roles/1/accept', { password: 'Password2026' })
    expect(client.post).toHaveBeenNthCalledWith(2, '/api/operators/roles/1/decline')
    expect(client.post).toHaveBeenNthCalledWith(3, '/api/organizations/invitations/2/accept')
    expect(client.post).toHaveBeenNthCalledWith(4, '/api/organizations/invitations/2/decline')
    expect(client.post).toHaveBeenNthCalledWith(5, '/api/topics/3/collaborators/accept')
    expect(client.post).toHaveBeenNthCalledWith(6, '/api/topics/3/collaborators/decline')
    expect(client.post).toHaveBeenNthCalledWith(7, '/api/organizations/ownership-transfers/4/accept')
    expect(client.post).toHaveBeenNthCalledWith(8, '/api/organizations/ownership-transfers/4/decline')
  })
})
