import type { IdentitySummary } from '@shared/types'

export type ManagementSectionId =
  | 'platform-roles'
  | 'organization-reviews'
  | 'organization-members'
  | 'activity-collaborators'

export function deriveManagementSections(
  identity?: IdentitySummary | null,
): ManagementSectionId[] {
  if (!identity) return []

  const isOperator = Boolean(identity.platform_role)
  const ownsOrganization = identity.organization_roles.some(({ role }) => role === 'owner')
  const managesTopic = identity.topic_roles.some(({ role }) => role === 'manager')
  const sections: ManagementSectionId[] = []

  if (isOperator) {
    sections.push('platform-roles', 'organization-reviews')
  }
  if (ownsOrganization) {
    sections.push('organization-members')
  }
  if (isOperator || ownsOrganization || managesTopic) {
    sections.push('activity-collaborators')
  }

  return sections
}

export function hasManagementAccess(identity?: IdentitySummary | null): boolean {
  return deriveManagementSections(identity).length > 0
}
