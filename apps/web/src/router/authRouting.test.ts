import { describe, expect, it } from 'vitest'
import { requiredRoute } from './authRouting'

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
