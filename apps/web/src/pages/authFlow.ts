import type { User } from '@shared/types'

export type AuthMode = 'login' | 'register' | 'reset'

interface AuthRequestToken {
  generation: number
  mode: AuthMode
}

export interface AuthRequestTracker {
  begin: () => AuthRequestToken
  switchMode: (mode: AuthMode) => void
  commit: (request: AuthRequestToken, effect: () => void) => boolean
}

export function createAuthRequestTracker(initialMode: AuthMode): AuthRequestTracker {
  let mode = initialMode
  let generation = 0

  const isCurrent = (request: AuthRequestToken) =>
    request.mode === mode && request.generation === generation

  return {
    begin() {
      generation += 1
      return { generation, mode }
    },
    switchMode(nextMode) {
      if (nextMode === mode) return
      mode = nextMode
      generation += 1
    },
    commit(request, effect) {
      if (!isCurrent(request)) return false
      effect()
      return true
    },
  }
}

export function passwordForMode(value: string, owner: AuthMode, activeMode: AuthMode) {
  return owner === activeMode ? value : ''
}

export function destinationAfterAuth(user: User): '/onboarding' | '/home' {
  return user.onboarding_completed ? '/home' : '/onboarding'
}

export function successfulAuthNavigation(user: User) {
  return {
    to: destinationAfterAuth(user),
    replace: true as const,
  }
}
