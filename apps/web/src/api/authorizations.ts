import type {
  ApiResponse,
  OrganizationInvitationSummary,
  OwnershipTransferSummary,
  PaginatedResponse,
  PlatformRoleGrant,
  TopicCollaborationInvitation,
  PostCollaborationInvitation,
  OrganizationApplicationSummary,
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

export function getMyPostCollaborations() {
  return responseData<PaginatedResponse<PostCollaborationInvitation>>(
    client.get('/api/posts/collaborations/my', { params: { status: 'pending' } }),
  )
}

export function acceptPostCollaboration(postId: string) {
  return responseData<PostCollaborationInvitation>(client.post(`/api/posts/${postId}/collaborators/accept`))
}

export function declinePostCollaboration(postId: string) {
  return responseData<PostCollaborationInvitation>(client.post(`/api/posts/${postId}/collaborators/decline`))
}

export function getMyOrganizationApplications() {
  return responseData<PaginatedResponse<OrganizationApplicationSummary>>(
    client.get('/api/organizations/applications/my'),
  )
}

export function submitOrganizationApplication(body: {
  organization_name: string
  org_type: 'student_org' | 'department' | 'laboratory' | 'administrative' | 'other'
  school_scope: string
  official_email?: string
  official_page?: string
  responsible_person_statement: string
  evidence_reference?: string
  evidence?: string
}) {
  return responseData<OrganizationApplicationSummary>(client.post('/api/organizations/applications', body))
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
