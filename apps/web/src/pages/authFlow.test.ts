import { describe, expect, it } from 'vitest'
import { destinationAfterAuth } from './authFlow'

describe('destinationAfterAuth', () => {
  it('sends incomplete users to onboarding', () => {
    expect(destinationAfterAuth({ onboarding_completed: false } as never)).toBe('/onboarding')
  })

  it('sends complete users home', () => {
    expect(destinationAfterAuth({ onboarding_completed: true } as never)).toBe('/home')
  })
})
