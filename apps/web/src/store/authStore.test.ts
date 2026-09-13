// @vitest-environment jsdom

import { describe, expect, it } from 'vitest'
import { migrateAuthState, useAuthStore } from './authStore'

describe('migrateAuthState', () => {
  it('clears saved publishing drafts on logout even outside the publish page', () => {
    sessionStorage.setItem('campusmate.publish.v2:1:topic_team:2', 'draft')
    sessionStorage.setItem('campusmate.publish.v2:1:casual_invitation:', 'draft')
    sessionStorage.setItem('unrelated', 'keep')
    useAuthStore.getState().logout()
    expect(sessionStorage.getItem('campusmate.publish.v2:1:topic_team:2')).toBeNull()
    expect(sessionStorage.getItem('campusmate.publish.v2:1:casual_invitation:')).toBeNull()
    expect(sessionStorage.getItem('unrelated')).toBe('keep')
    sessionStorage.clear()
  })
  it('invalidates a legacy authenticated user without an onboarding decision', () => {
    const legacyState = {
      token: 'legacy-token',
      user: { id: 'legacy-user', email: 'legacy@smail.nju.edu.cn' },
      isAuthenticated: true,
    }

    expect(migrateAuthState(legacyState, 0)).toEqual({
      token: null,
      user: null,
      isAuthenticated: false,
    })
  })

  it('hydrates a version-zero legacy session as logged out', async () => {
    localStorage.setItem(
      'campusmate-auth',
      JSON.stringify({
        state: {
          token: 'legacy-token',
          user: { id: 'legacy-user', email: 'legacy@smail.nju.edu.cn' },
          isAuthenticated: true,
        },
        version: 0,
      }),
    )

    await useAuthStore.persist.rehydrate()

    expect(useAuthStore.getState()).toMatchObject({
      token: null,
      user: null,
      isAuthenticated: false,
    })
    expect(useAuthStore.getState().setAuth).toBeTypeOf('function')
  })
})
