import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User } from '@shared/types'

interface AuthState {
  token: string | null
  user: User | null
  isAuthenticated: boolean
  setAuth: (token: string, user: User) => void
  setUser: (user: User) => void
  updateUser: (user: Partial<User>) => void
  logout: () => void
}

export function migrateAuthState(persistedState: unknown, _version: number): AuthState {
  const state = persistedState as Partial<AuthState>

  if (state.user && typeof state.user.onboarding_completed !== 'boolean') {
    return {
      token: null,
      user: null,
      isAuthenticated: false,
    } as AuthState
  }

  return state as AuthState
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      isAuthenticated: false,
      setAuth: (token, user) => set({ token, user, isAuthenticated: true }),
      setUser: (user) => set({ user }),
      updateUser: (partial) =>
        set((state) => ({
          user: state.user ? { ...state.user, ...partial } : null,
        })),
      logout: () => {
        try {
          for (const key of Object.keys(sessionStorage)) {
            if (key.startsWith('campusmate.publish.v2:')) sessionStorage.removeItem(key)
          }
        } catch { /* Storage can be disabled by the browser. */ }
        set({ token: null, user: null, isAuthenticated: false })
      },
    }),
    {
      name: 'campusmate-auth',
      version: 1,
      migrate: migrateAuthState,
    },
  ),
)
