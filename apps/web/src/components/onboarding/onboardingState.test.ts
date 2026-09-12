import { describe, expect, it } from 'vitest'
import type { OnboardingDraft } from '@shared/types'
import { canContinue } from './onboardingState'

describe('canContinue', () => {
  it('requires nickname on step one', () => {
    expect(canContinue(1, { nickname: '' } as OnboardingDraft)).toBe(false)
  })

  it('requires three unique interests on step three', () => {
    expect(canContinue(3, { interests: ['AI', 'AI', '跑步'] } as OnboardingDraft)).toBe(false)
    expect(canContinue(3, { interests: ['AI', '产品', '跑步'] } as OnboardingDraft)).toBe(true)
  })

  it('allows optional steps five and six', () => {
    expect(canContinue(5, {} as OnboardingDraft)).toBe(true)
    expect(canContinue(6, {} as OnboardingDraft)).toBe(true)
  })
})
