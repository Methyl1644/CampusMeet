import type { OnboardingDraft, OnboardingUpdate, User } from '@shared/types'
import { get, patch, post } from './client'

const ONBOARDING_PATH = '/api/auth/onboarding'

export function getOnboarding() {
  return get<OnboardingDraft>(ONBOARDING_PATH)
}

export function saveOnboarding(payload: OnboardingUpdate) {
  return patch<OnboardingDraft>(ONBOARDING_PATH, payload)
}

export function completeOnboarding() {
  return post<User>(`${ONBOARDING_PATH}/complete`)
}
