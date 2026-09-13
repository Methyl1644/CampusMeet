import { describe, expect, it } from 'vitest'
import { personalRedirectTarget } from '@/pages/ProfileRedirect'

describe('legacy profile route compatibility', () => {
  it.each([
    ['?tab=events', '/my/activities'],
    ['?tab=groups', '/my/groups'],
    ['?view=notifications', '/notifications'],
    ['?view=settings', '/settings'],
    ['?view=public', '/users/me'],
    ['', '/users/me'],
    ['?view=unknown', '/users/me'],
  ])('maps %s to %s', (search, expected) => {
    expect(personalRedirectTarget(new URLSearchParams(search))).toBe(expected)
  })
})
