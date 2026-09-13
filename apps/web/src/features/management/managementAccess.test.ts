import { describe, expect, it } from 'vitest'
import type { IdentitySummary } from '@shared/types'
import { deriveManagementSections } from './managementAccess'

const identity = (overrides: Partial<IdentitySummary> = {}): IdentitySummary => ({
  campus_verified: true,
  platform_role: null,
  organization_roles: [],
  topic_roles: [],
  post_roles: [],
  ...overrides,
})

describe('deriveManagementSections', () => {
  it('keeps ordinary allowlisted users outside the management center', () => {
    expect(deriveManagementSections(identity())).toEqual([])
  })

  it('gives platform operators the platform, review, and collaborator sections', () => {
    expect(deriveManagementSections(identity({ platform_role: 'operator' }))).toEqual([
      'platform-roles',
      'organization-reviews',
      'activity-collaborators',
    ])
  })

  it('gives organization owners member and collaborator management', () => {
    expect(deriveManagementSections(identity({
      organization_roles: [{ organization_id: '7', organization_name: '校科协', role: 'owner' }],
    }))).toEqual(['organization-members', 'activity-collaborators'])
  })

  it('gives topic managers collaborator management only', () => {
    expect(deriveManagementSections(identity({
      topic_roles: [{ topic_id: '9', topic_title: '挑战杯', role: 'manager' }],
    }))).toEqual(['activity-collaborators'])
  })
})
