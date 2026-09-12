// @vitest-environment jsdom

import { describe, expect, it } from 'vitest'
import { migrateAuthState, useAuthStore } from './authStore'

describe('migrateAuthState', () => {
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
