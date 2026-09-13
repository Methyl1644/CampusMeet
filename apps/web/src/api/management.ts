import { API_PATHS } from '@shared/constants'
import type {
  ApiResponse,
  CollaboratorGrant,
  ManagedOrganization,
  ManagementPermissions,
  OrganizationApplicationSummary,
  OrganizationMemberSummary,
  PaginatedResponse,
  PlatformRole,
  PlatformRoleGrant,
  TopicRole,
} from '@shared/types'
import { client } from './client'

async function responseData<T>(request: Promise<{ data: ApiResponse<T> }>): Promise<T> {
  return (await request).data.data
}

export function getManagementPermissions() {
  return responseData<ManagementPermissions>(client.get(API_PATHS.content.permissions))
}

export function getPlatformRoles(status = 'all') {
  return responseData<PaginatedResponse<PlatformRoleGrant>>(
    client.get(API_PATHS.operators.roles, { params: { status } }),
  )
}

export function invitePlatformRole(body: { user_id: number; role: PlatformRole }) {
  return responseData<PlatformRoleGrant>(client.post(API_PATHS.operators.invitations, body))
}

export function suspendPlatformRole(grantId: string, reason: string) {
  return responseData<PlatformRoleGrant>(client.post(
    API_PATHS.operators.suspendRole.replace(':id', grantId),
    { reason },
  ))
}

export function revokePlatformRole(grantId: string, reason: string) {
  return responseData<PlatformRoleGrant>(client.post(
    API_PATHS.operators.revokeRole.replace(':id', grantId),
    { reason },
  ))
}

export function getOrganizationApplications(status = 'pending') {
  return responseData<PaginatedResponse<OrganizationApplicationSummary>>(
    client.get(API_PATHS.identity.applicationQueue, { params: { status } }),
  )
}

export function reviewOrganizationApplication(
  applicationId: string,
  body: { decision: 'approve' | 'reject'; reason: string; validity_days: number },
) {
  return responseData<{ application_id: string; status: string; organization_id?: string | null }>(
    client.post(`/api/operators/organization-applications/${applicationId}/review`, body),
  )
}

export function getManagedOrganizations() {
  return responseData<ManagedOrganization[]>(client.get(API_PATHS.identity.managedOrganizations))
}

export function getOrganizationMembers(organizationId: string) {
  return responseData<PaginatedResponse<OrganizationMemberSummary>>(
    client.get(`/api/organizations/${organizationId}/members`),
  )
}

export function inviteOrganizationMember(
  organizationId: string,
  body: { user_id: number; role: 'publisher' | 'member' },
) {
  return responseData<unknown>(client.post(`/api/organizations/${organizationId}/invitations`, body))
}

export function revokeOrganizationMember(organizationId: string, userId: string) {
  return responseData<{ user_id: string; status: string }>(
    client.delete(`/api/organizations/${organizationId}/members/${userId}`),
  )
}

export function transferOrganizationOwnership(organizationId: string, targetUserId: string) {
  return responseData<unknown>(client.post(`/api/organizations/${organizationId}/ownership-transfers`, {
    target_user_id: Number(targetUserId),
  }))
}

export function getTopicCollaborators(topicId: string) {
  return responseData<PaginatedResponse<CollaboratorGrant>>(
    client.get(`/api/topics/${topicId}/collaborators`),
  )
}

export function inviteTopicCollaborator(
  topicId: string,
  body: { user_id: number; role: TopicRole },
) {
  return responseData<CollaboratorGrant>(client.post(`/api/topics/${topicId}/collaborators`, body))
}

export function revokeTopicCollaborator(topicId: string, userId: string) {
  return responseData<CollaboratorGrant>(
    client.delete(`/api/topics/${topicId}/collaborators/${userId}`),
  )
}
