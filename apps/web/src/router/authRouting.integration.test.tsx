// @vitest-environment jsdom

import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
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

vi.mock('@/api/home', () => ({
  getHomeFeed: vi.fn().mockResolvedValue({
    profile: { id: '1', nickname: '小紫', avatar: null, major: null, grade: null },
    deadline_reminder: null,
    recommended_topics: [],
    attending_topics: [],
    followed_topics: [],
    joined_groups: [],
    group_timeline: [],
    unread: { messages: 0, notifications: 0 },
    warnings: [],
  }),
}))

vi.mock('@/pages/Home', () => ({
  default: () => <h1>Home route</h1>,
}))

const defaultVisibility = {
  major: true,
  grade: true,
  interests: true,
  skills: true,
  availability: false,
  contact: false,
}

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
  profile_visibility: defaultVisibility,
} as User

const completeUser = {
  ...incompleteUser,
  nickname: '小紫',
  major: '软件学院',
  grade: '本科三年级',
  onboarding_step: 6,
  onboarding_completed: true,
  interests: ['人工智能', '数学建模', '羽毛球'],
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
  profile_visibility: defaultVisibility,
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

  it.each(['/onboarding/', '/OnBoArDiNg'])(
    'redirects completed users from equivalent onboarding path %s without loading a draft',
    async (path) => {
      useAuthStore.setState({ token: 'token', user: completeUser, isAuthenticated: true })
      const history = renderRoute(['/history-marker', path])

      await waitFor(() => expect(history.pathname()).toBe('/home'))
      expect(screen.queryByRole('progressbar')).toBeNull()
      expect(getOnboarding).not.toHaveBeenCalled()
      await history.back()
      await waitFor(() => expect(history.pathname()).toBe('/history-marker'))
    },
  )

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

  it('merges a cross-device completed draft before the first home render', async () => {
    const completedDraft = {
      onboarding_step: 6,
      onboarding_completed: true,
      nickname: '服务端昵称',
      avatar: 'https://example.test/avatar.png',
      major: '计算机科学与技术',
      grade: '本科四年级',
      interests: ['人工智能', '数学建模', '羽毛球'],
      looking_for: ['科研合作'],
      skills: ['Python'],
      availability: { weekday_evening: true, weekly_hours: '每周 4-6 小时' },
      bio: '服务端简介',
      profile_visibility: { ...defaultVisibility, major: false },
    } satisfies OnboardingDraft
    vi.mocked(getOnboarding).mockResolvedValue(completedDraft)
    useAuthStore.setState({ token: 'token', user: incompleteUser, isAuthenticated: true })
    let userAtFirstHomeRender: User | null = null
    const history = renderRoute(['/onboarding'], 0, (user) => {
      if (!userAtFirstHomeRender) userAtFirstHomeRender = user
    })

    await waitFor(() => expect(history.pathname()).toBe('/home'))

    const expectedUser = { ...incompleteUser, ...completedDraft }
    expect(userAtFirstHomeRender).toEqual(expectedUser)
    expect(useAuthStore.getState().user).toEqual(expectedUser)
  })

  it('moves focus to the new stage heading after Continue and Back', async () => {
    vi.mocked(getOnboarding).mockResolvedValue({
      ...draft,
      onboarding_step: 2,
      nickname: '小紫',
      major: '软件工程',
      grade: '本科三年级',
      interests: ['人工智能', '数学建模', '羽毛球'],
    })
    useAuthStore.setState({ token: 'token', user: incompleteUser, isAuthenticated: true })
    renderRoute(['/onboarding'])
    await screen.findByRole('heading', { name: '你在南大的学习坐标' })

    fireEvent.click(screen.getByRole('button', { name: '继续' }))
    const interestHeading = await screen.findByRole('heading', { name: '最近有哪些方向吸引你？' })
    await waitFor(() => expect(document.activeElement).toBe(interestHeading))

    fireEvent.click(screen.getByRole('button', { name: '返回上一步' }))
    const campusHeading = await screen.findByRole('heading', { name: '你在南大的学习坐标' })
    await waitFor(() => expect(document.activeElement).toBe(campusHeading))
  })

  it('keeps stage focus movement when reduced motion is requested', async () => {
    vi.stubGlobal('matchMedia', (query: string) => ({
      matches: query.includes('prefers-reduced-motion'),
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }))
    vi.mocked(getOnboarding).mockResolvedValue({
      ...draft,
      onboarding_step: 5,
      nickname: '小紫',
      major: '软件工程',
      grade: '本科三年级',
      interests: ['人工智能', '数学建模', '羽毛球'],
    })
    useAuthStore.setState({ token: 'token', user: incompleteUser, isAuthenticated: true })
    renderRoute(['/onboarding'])
    await screen.findByRole('heading', { name: '把你的节奏告诉未来队友' })

    fireEvent.click(screen.getByRole('button', { name: '继续' }))
    const previewHeading = await screen.findByRole('heading', { name: '看看大家会如何认识你' })

    await waitFor(() => expect(document.activeElement).toBe(previewHeading))
    vi.unstubAllGlobals()
  })

  it('keeps contact private by default and saves the preview choice', async () => {
    const privateUser = {
      ...incompleteUser,
      phone: '13800138000',
      wechat: 'private_wechat',
    } as User
    vi.mocked(getOnboarding).mockResolvedValue({
      ...draft,
      onboarding_step: 6,
      nickname: '小紫',
      major: '软件工程',
      grade: '本科三年级',
      interests: ['人工智能', '数学建模', '羽毛球'],
      profile_visibility: defaultVisibility,
    })
    useAuthStore.setState({ token: 'token', user: privateUser, isAuthenticated: true })
    renderRoute(['/onboarding'])

    const contactVisibility = await screen.findByRole('checkbox', { name: '联系方式' })
    expect((contactVisibility as HTMLInputElement).checked).toBe(false)
    expect(screen.queryByText('13800138000')).toBeNull()
    expect(screen.queryByText('private_wechat')).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: '完成资料' }))
    await waitFor(() => expect(saveOnboarding).toHaveBeenCalled())
    expect(vi.mocked(saveOnboarding).mock.calls[0][0].profile_visibility?.contact).toBe(false)
  })
})
