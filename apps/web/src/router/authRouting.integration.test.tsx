// @vitest-environment jsdom

import { act, cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  MemoryRouter,
  useLocation,
  useNavigate,
  useRoutes,
  type NavigateFunction,
  type RouteObject,
} from 'react-router-dom'
import { ToastProvider } from '@/components/Toast'
import { completeOnboarding, getOnboarding, saveOnboarding } from '@/api/onboarding'
import { useAuthStore } from '@/store/authStore'
import type { OnboardingDraft, User } from '@shared/types'
import * as routerModule from './index'

vi.mock('@/api/onboarding', () => ({
  getOnboarding: vi.fn(),
  saveOnboarding: vi.fn(),
  completeOnboarding: vi.fn(),
}))

vi.mock('@/pages/Home', () => ({
  default: () => <h1>Home route</h1>,
}))

const incompleteUser = {
  id: '1',
  email: 'student@smail.nju.edu.cn',
  nickname: 'student',
  auth_status: 'unverified',
  skills: [],
  onboarding_step: 1,
  onboarding_completed: false,
  interests: [],
  looking_for: [],
  availability: {},
  profile_visibility: {},
} as User

const completeUser = {
  ...incompleteUser,
  nickname: '小紫',
  major: '软件学院',
  grade: '本科三年级',
  onboarding_step: 6,
  onboarding_completed: true,
  interests: ['人工智能', '产品设计', '羽毛球'],
} as User

const draft = {
  onboarding_step: 1,
  onboarding_completed: false,
  nickname: '',
  avatar: '',
  major: '',
  grade: '',
  interests: [],
  looking_for: [],
  skills: [],
  availability: {},
  bio: '',
  profile_visibility: {},
} satisfies OnboardingDraft

function appRoutes(): RouteObject[] {
  const routes = (routerModule as typeof routerModule & { appRoutes?: RouteObject[] }).appRoutes
  expect(routes).toBeDefined()
  return routes!
}

function RouteHarness({ onHome }: { onHome?: (user: User | null) => void }) {
  const location = useLocation()
  const navigate = useNavigate()
  const route = useRoutes([
    ...appRoutes(),
    { path: '/history-marker', element: <span>History marker</span> },
  ])
  activeNavigate = navigate
  if (location.pathname === '/home') onHome?.(useAuthStore.getState().user)

  return (
    <>
      <output data-testid="route-location">{location.pathname}</output>
      {route}
    </>
  )
}

let activeNavigate: NavigateFunction | null = null

function renderRoute(
  initialEntries: string[],
  initialIndex = initialEntries.length - 1,
  onHome?: (user: User | null) => void,
) {
  render(
    <MemoryRouter
      initialEntries={initialEntries}
      initialIndex={initialIndex}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <ToastProvider>
        <RouteHarness onHome={onHome} />
      </ToastProvider>
    </MemoryRouter>,
  )
  return {
    pathname: () => screen.getByTestId('route-location').textContent,
    back: async () => {
      await act(async () => activeNavigate?.(-1))
    },
  }
}

beforeEach(() => {
  localStorage.clear()
  useAuthStore.setState({ token: null, user: null, isAuthenticated: false })
  vi.mocked(getOnboarding).mockResolvedValue(draft)
  vi.mocked(saveOnboarding).mockImplementation(async (payload) => ({ ...draft, ...payload }))
  vi.mocked(completeOnboarding).mockResolvedValue(completeUser)
})

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('application route guards', () => {
  it('replaces anonymous onboarding history with login', async () => {
    const history = renderRoute(['/history-marker', '/onboarding'])

    await waitFor(() => expect(history.pathname()).toBe('/login'))
    await history.back()
    await waitFor(() => expect(history.pathname()).toBe('/history-marker'))
  })

  it('redirects an incomplete user from a main route before rendering MainLayout', async () => {
    useAuthStore.setState({ token: 'token', user: incompleteUser, isAuthenticated: true })
    const history = renderRoute(['/home'])

    await waitFor(() => expect(history.pathname()).toBe('/onboarding'))
    expect(screen.queryByRole('navigation')).toBeNull()
    expect((await screen.findByRole('progressbar')).getAttribute('aria-valuenow')).toBe('1')
  })

  it('renders onboarding outside the MainLayout hierarchy', async () => {
    useAuthStore.setState({ token: 'token', user: incompleteUser, isAuthenticated: true })
    const history = renderRoute(['/onboarding'])

    expect(history.pathname()).toBe('/onboarding')
    expect(await screen.findByRole('progressbar')).toBeTruthy()
    expect(screen.queryByRole('navigation')).toBeNull()
  })

  it('replaces completed-user onboarding history with home', async () => {
    useAuthStore.setState({ token: 'token', user: completeUser, isAuthenticated: true })
    const history = renderRoute(['/history-marker', '/onboarding'])

    await waitFor(() => expect(history.pathname()).toBe('/home'))
    await history.back()
    await waitFor(() => expect(history.pathname()).toBe('/history-marker'))
  })

  it('keeps an authenticated complete user out of login history', async () => {
    useAuthStore.setState({ token: 'token', user: completeUser, isAuthenticated: true })
    const history = renderRoute(['/history-marker', '/login'])

    await waitFor(() => expect(history.pathname()).toBe('/home'))
    await history.back()
    await waitFor(() => expect(history.pathname()).toBe('/history-marker'))
  })

  it('stores the authoritative completed user before the first home navigation', async () => {
    const stageSix = { ...draft, ...completeUser, onboarding_completed: false } as OnboardingDraft
    vi.mocked(getOnboarding).mockResolvedValue(stageSix)
    useAuthStore.setState({ token: 'token', user: incompleteUser, isAuthenticated: true })
    let userAtHomeNavigation: User | null = null
    const history = renderRoute(['/onboarding'], 0, (user) => {
      if (!userAtHomeNavigation) userAtHomeNavigation = user
    })

    await screen.findByRole('button', { name: '完成资料' })
    await screen.getByRole('button', { name: '完成资料' }).click()
    await waitFor(() => expect(history.pathname()).toBe('/home'))

    expect(userAtHomeNavigation).toEqual(completeUser)
    expect(useAuthStore.getState().user).toEqual(completeUser)
  })
})
