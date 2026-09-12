import { describe, expect, it } from 'vitest'
import type { OnboardingDraft } from '@shared/types'
import { canContinue, canEditOnboarding, canEnterOnboarding } from './onboardingState'

describe('canEnterOnboarding', () => {
  it('blocks editing until an authoritative draft is loaded', () => {
    const emailPrefixFallback = { nickname: 'student' } as OnboardingDraft
    const authoritativeDraft = { nickname: '小紫' } as OnboardingDraft

    expect(canEnterOnboarding('loading', null)).toBe(false)
    expect(canEnterOnboarding('error', emailPrefixFallback)).toBe(false)
    expect(canEnterOnboarding('ready', null)).toBe(false)
    expect(canEnterOnboarding('ready', authoritativeDraft)).toBe(true)
  })
})

describe('canEditOnboarding', () => {
  it('locks every field while an authoritative draft is saving', () => {
    const authoritativeDraft = { nickname: '小紫' } as OnboardingDraft

    expect(canEditOnboarding('ready', authoritativeDraft, false)).toBe(true)
    expect(canEditOnboarding('ready', authoritativeDraft, true)).toBe(false)
    expect(canEditOnboarding('loading', null, false)).toBe(false)
    expect(canEditOnboarding('error', null, false)).toBe(false)
  })
})

describe('canContinue', () => {
  it('requires nickname on step one', () => {
    expect(canContinue(1, { nickname: '' } as OnboardingDraft)).toBe(false)
  })

  it('requires three unique interests on step three', () => {
    expect(canContinue(3, { interests: ['AI', 'AI', '跑步'] } as OnboardingDraft)).toBe(false)
    expect(canContinue(3, { interests: ['AI', '产品', '跑步'] } as OnboardingDraft)).toBe(true)
  })

  it('allows optional steps four, five and six', () => {
    expect(canContinue(4, {} as OnboardingDraft)).toBe(true)
    expect(canContinue(5, {} as OnboardingDraft)).toBe(true)
    expect(canContinue(6, {} as OnboardingDraft)).toBe(true)
  })
})
