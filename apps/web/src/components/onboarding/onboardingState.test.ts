import { describe, expect, it } from 'vitest'
import { ONBOARDING_INTERESTS } from '@shared/constants'
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

  it('requires three to thirty unique standard interests on step three', () => {
    expect(canContinue(3, {
      interests: ['人工智能', '人工智能', '数学建模'],
    } as OnboardingDraft)).toBe(false)
    expect(canContinue(3, {
      interests: ['人工智能', '数学建模', '羽毛球'],
    } as OnboardingDraft)).toBe(true)
    expect(canContinue(3, {
      interests: [...ONBOARDING_INTERESTS.slice(0, 30)],
    } as OnboardingDraft)).toBe(true)
    expect(canContinue(3, {
      interests: [...ONBOARDING_INTERESTS.slice(0, 31)],
    } as OnboardingDraft)).toBe(false)
    expect(canContinue(3, {
      interests: ['自造兴趣一', '自造兴趣二', '自造兴趣三'],
    } as OnboardingDraft)).toBe(false)
  })

  it('allows optional steps four, five and six', () => {
    expect(canContinue(4, {} as OnboardingDraft)).toBe(true)
    expect(canContinue(5, {} as OnboardingDraft)).toBe(true)
    expect(canContinue(6, {} as OnboardingDraft)).toBe(true)
  })
})
