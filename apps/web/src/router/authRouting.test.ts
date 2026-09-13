import { describe, expect, it } from 'vitest'
import * as authRouting from './authRouting'

const { requiredRoute } = authRouting
const subject = authRouting as typeof authRouting & {
  commitCompletedOnboarding?: (
    user: never,
    setUser: (user: never) => void,
    navigate: (to: string, options: { replace: boolean }) => void,
  ) => void
}

describe('requiredRoute', () => {
  it('keeps incomplete users inside onboarding', () => {
    expect(requiredRoute({ onboarding_completed: false } as never, '/home')).toBe('/onboarding')
  })

  it('keeps complete users out of onboarding', () => {
    expect(requiredRoute({ onboarding_completed: true } as never, '/onboarding')).toBe('/home')
  })

  it('does not redirect a valid complete-user route', () => {
    expect(requiredRoute({ onboarding_completed: true } as never, '/discover')).toBeNull()
  })
})

describe('commitCompletedOnboarding', () => {
  it('replaces the store user before replacing onboarding history with home', () => {
    expect(subject.commitCompletedOnboarding).toBeTypeOf('function')
    const events: string[] = []
    const user = { onboarding_completed: true } as never

    subject.commitCompletedOnboarding!(
      user,
      (storedUser) => events.push(storedUser === user ? 'store' : 'wrong-user'),
      (to, options) => events.push(`${to}:${options.replace}`),
    )

    expect(events).toEqual(['store', '/home:true'])
  })
})
