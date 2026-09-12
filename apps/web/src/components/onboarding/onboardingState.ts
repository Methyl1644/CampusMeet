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

const uniqueNonEmptyCount = (values?: string[]) =>
  new Set(values?.map((value) => value.trim()).filter(Boolean)).size

export function canContinue(step: number, draft: OnboardingDraft): boolean {
  switch (step) {
    case 1:
      return hasText(draft.nickname)
    case 2:
      return hasText(draft.major) && hasText(draft.grade)
    case 3:
      return uniqueNonEmptyCount(draft.interests) >= 3
    case 4:
    case 5:
    case 6:
      return true
    default:
      return false
  }
}
