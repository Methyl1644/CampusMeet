import type {
  ApiResponse,
  OrganizationInvitationSummary,
  OwnershipTransferSummary,
  PaginatedResponse,
  PlatformRoleGrant,
  TopicCollaborationInvitation,
} from '@shared/types'
import { client } from './client'

async function responseData<T>(request: Promise<{ data: ApiResponse<T> }>): Promise<T> {
  return (await request).data.data
}

export function getMyPlatformRoles() {
  return responseData<PaginatedResponse<PlatformRoleGrant>>(
    client.get('/api/operators/roles/my', { params: { status: 'pending' } }),
  )
}

export function acceptPlatformRole(grantId: string, password: string) {
  return responseData<PlatformRoleGrant>(client.post(`/api/operators/roles/${grantId}/accept`, { password }))
}

export function declinePlatformRole(grantId: string) {
  return responseData<PlatformRoleGrant>(client.post(`/api/operators/roles/${grantId}/decline`))
}

export function getMyOrganizationInvitations() {
  return responseData<PaginatedResponse<OrganizationInvitationSummary>>(
    client.get('/api/organizations/invitations/my', { params: { status: 'pending' } }),
  )
}

export function acceptOrganizationInvitation(invitationId: string) {
  return responseData<OrganizationInvitationSummary>(client.post(`/api/organizations/invitations/${invitationId}/accept`))
}

export function declineOrganizationInvitation(invitationId: string) {
  return responseData<OrganizationInvitationSummary>(client.post(`/api/organizations/invitations/${invitationId}/decline`))
}

export function getMyTopicCollaborations() {
  return responseData<PaginatedResponse<TopicCollaborationInvitation>>(
    client.get('/api/topics/collaborations/my', { params: { status: 'pending' } }),
  )
}

export function acceptTopicCollaboration(topicId: string) {
  return responseData<TopicCollaborationInvitation>(client.post(`/api/topics/${topicId}/collaborators/accept`))
}

export function declineTopicCollaboration(topicId: string) {
  return responseData<TopicCollaborationInvitation>(client.post(`/api/topics/${topicId}/collaborators/decline`))
}

export function getMyOwnershipTransfers() {
  return responseData<PaginatedResponse<OwnershipTransferSummary>>(
    client.get('/api/organizations/ownership-transfers/my', { params: { status: 'pending' } }),
  )
}

export function acceptOwnershipTransfer(transferId: string) {
  return responseData<OwnershipTransferSummary>(client.post(`/api/organizations/ownership-transfers/${transferId}/accept`))
}

export function declineOwnershipTransfer(transferId: string) {
  return responseData<OwnershipTransferSummary>(client.post(`/api/organizations/ownership-transfers/${transferId}/decline`))
}
