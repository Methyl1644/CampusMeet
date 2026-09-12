import type { User } from '@shared/types'

export function destinationAfterAuth(user: User): '/onboarding' | '/home' {
  return user.onboarding_completed ? '/home' : '/onboarding'
}
