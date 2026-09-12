import { describe, expect, it } from 'vitest'
import * as authFlow from './authFlow'

type AuthMode = 'login' | 'register' | 'reset'

interface RequestTracker {
  begin: () => unknown
  switchMode: (mode: AuthMode) => void
  commit: (request: unknown, effect: () => void) => boolean
}

const subject = authFlow as typeof authFlow & {
  createAuthRequestTracker?: (initialMode: AuthMode) => RequestTracker
  passwordForMode?: (value: string, owner: AuthMode, activeMode: AuthMode) => string
  successfulAuthNavigation?: (user: never) => {
    to: '/onboarding' | '/home'
    replace: boolean
  }
}

function createTracker(initialMode: AuthMode) {
  expect(subject.createAuthRequestTracker).toBeTypeOf('function')
  return subject.createAuthRequestTracker!(initialMode)
}

describe('destinationAfterAuth', () => {
  it('sends incomplete users to onboarding', () => {
    expect(authFlow.destinationAfterAuth({ onboarding_completed: false } as never)).toBe('/onboarding')
  })

  it('sends complete users home', () => {
    expect(authFlow.destinationAfterAuth({ onboarding_completed: true } as never)).toBe('/home')
  })
})

describe('successfulAuthNavigation', () => {
  it('replaces login history when an incomplete user enters onboarding', () => {
    expect(subject.successfulAuthNavigation).toBeTypeOf('function')
    expect(subject.successfulAuthNavigation!({ onboarding_completed: false } as never)).toEqual({
      to: '/onboarding',
      replace: true,
    })
  })

  it('replaces login history when a complete user enters home', () => {
    expect(subject.successfulAuthNavigation).toBeTypeOf('function')
    expect(subject.successfulAuthNavigation!({ onboarding_completed: true } as never)).toEqual({
      to: '/home',
      replace: true,
    })
  })
})

describe('authentication request tracking', () => {
  it('suppresses stale effects after every authentication mode change', () => {
    const tracker = createTracker('login')
    const effects: string[] = []

    const loginRequest = tracker.begin()
    tracker.switchMode('register')
    expect(tracker.commit(loginRequest, () => effects.push('login'))).toBe(false)

    const registrationRequest = tracker.begin()
    tracker.switchMode('reset')
    expect(tracker.commit(registrationRequest, () => effects.push('register'))).toBe(false)

    const resetRequest = tracker.begin()
    tracker.switchMode('login')
    expect(tracker.commit(resetRequest, () => effects.push('reset'))).toBe(false)

    expect(effects).toEqual([])
  })

  it('allows only the latest request in the current mode to commit effects', () => {
    const tracker = createTracker('login')
    const effects: string[] = []
    const firstRequest = tracker.begin()
    const secondRequest = tracker.begin()

    expect(tracker.commit(firstRequest, () => effects.push('first'))).toBe(false)
    expect(tracker.commit(secondRequest, () => effects.push('second'))).toBe(true)
    expect(effects).toEqual(['second'])
  })
})

describe('passwordForMode', () => {
  it('clears a password when switching away from its owning mode', () => {
    expect(subject.passwordForMode).toBeTypeOf('function')

    expect(subject.passwordForMode!('login-secret', 'login', 'register')).toBe('')
    expect(subject.passwordForMode!('register-secret', 'register', 'reset')).toBe('')
    expect(subject.passwordForMode!('reset-secret', 'reset', 'login')).toBe('')
  })

  it('retains a password only while its owning mode remains active', () => {
    expect(subject.passwordForMode).toBeTypeOf('function')

    expect(subject.passwordForMode!('login-secret', 'login', 'login')).toBe('login-secret')
    expect(subject.passwordForMode!('register-secret', 'register', 'register')).toBe(
      'register-secret',
    )
    expect(subject.passwordForMode!('reset-secret', 'reset', 'reset')).toBe('reset-secret')
  })
})
