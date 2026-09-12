import type { User } from '@shared/types'

export function requiredRoute(user: User, requestedPath: string): string | null {
  if (!user.onboarding_completed && requestedPath !== '/onboarding') {
    return '/onboarding'
  }

  if (user.onboarding_completed && requestedPath === '/onboarding') {
    return '/home'
  }

  return null
}

export function commitCompletedOnboarding(
  user: User,
  setUser: (user: User) => void,
  navigate: (to: string, options: { replace: boolean }) => void,
) {
  setUser(user)
  navigate('/home', { replace: true })
}
