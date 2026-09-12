import type { OnboardingDraft } from '@shared/types'

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
      return uniqueNonEmptyCount(draft.looking_for) >= 1
    case 5:
    case 6:
      return true
    default:
      return false
  }
}
