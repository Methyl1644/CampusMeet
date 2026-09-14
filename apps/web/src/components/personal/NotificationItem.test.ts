import { describe, expect, it } from 'vitest'
import { notificationTarget } from './NotificationItem'

describe('authorization notification targets', () => {
  it('opens organization invitations in the authorization inbox', () => {
    expect(notificationTarget({
      id: '1',
      event_type: 'organization.invitation.created',
      title: '收到组织邀请',
      body: '邀请成为官方发布者',
      target_type: 'organization_invitation',
      target_id: '20',
      created_at: '2026-09-14T00:00:00Z',
    })).toBe('/authorizations')
  })
})
