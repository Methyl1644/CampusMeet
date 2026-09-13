import { ONBOARDING_INTERESTS } from '@shared/constants'
import type { OnboardingDraft } from '@shared/types'

export type OnboardingLoadStatus = 'loading' | 'ready' | 'error'

export function canEnterOnboarding(
  status: OnboardingLoadStatus,
  draft: OnboardingDraft | null,
): draft is OnboardingDraft {
  return status === 'ready' && draft !== null
}

export function canEditOnboarding(
  status: OnboardingLoadStatus,
  draft: OnboardingDraft | null,
  isSaving: boolean,
): boolean {
  return canEnterOnboarding(status, draft) && !isSaving
}

const hasText = (value?: string) => Boolean(value?.trim())

export const MIN_ONBOARDING_INTERESTS = 3
export const MAX_ONBOARDING_INTERESTS = 30

const standardInterests = new Set<string>(ONBOARDING_INTERESTS)

const uniqueStandardInterestCount = (values?: string[]) => {
  const normalized = values?.map((value) => value.trim()) ?? []
  if (
    normalized.length > MAX_ONBOARDING_INTERESTS
    || normalized.some((value) => !standardInterests.has(value))
  ) {
    return 0
  }
  return new Set(normalized).size
}

export function canContinue(step: number, draft: OnboardingDraft): boolean {
  switch (step) {
    case 1:
      return hasText(draft.nickname)
    case 2:
      return hasText(draft.major) && hasText(draft.grade)
    case 3: {
      const interestCount = uniqueStandardInterestCount(draft.interests)
      return interestCount >= MIN_ONBOARDING_INTERESTS && interestCount <= MAX_ONBOARDING_INTERESTS
    }
    case 4:
    case 5:
    case 6:
      return true
    default:
      return false
  }
}
