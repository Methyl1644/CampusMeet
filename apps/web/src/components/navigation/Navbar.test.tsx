// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  MemoryRouter,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from 'react-router-dom'
import type { HomeFeed, User } from '@shared/types'
import { getHomeFeed } from '@/api/home'
import Navbar from '@/components/Navbar'
import { useHomeFeed } from '@/features/home/HomeFeedContext'
import MainLayout from '@/layouts/MainLayout'
import { useAuthStore } from '@/store/authStore'

vi.mock('@/api/home', () => ({
  getHomeFeed: vi.fn(),
}))

const user: User = {
  id: 'student-1',
  nickname: '林晓',
  avatar: undefined,
  auth_status: 'campus_verified',
  email: 'lin@smail.nju.edu.cn',
  skills: [],
  onboarding_step: 4,
  onboarding_completed: true,
  interests: [],
  looking_for: [],
  availability: {
    weekly_hours: '',
  },
  profile_visibility: {
    major: true,
    grade: true,
    interests: true,
    skills: true,
    availability: true,
    contact: false,
  },
}

const feed: HomeFeed = {
  profile: {
    id: user.id,
    nickname: user.nickname,
    avatar: null,
    major: null,
    grade: null,
  },
  deadline_reminder: null,
  recommended_topics: [],
  followed_topics: [],
  joined_groups: [],
  group_timeline: [],
  unread: {
    messages: 2,
    notifications: 3,
  },
  warnings: [],
}

function LocationProbe() {
  const location = useLocation()
  return <output aria-label="当前位置">{`${location.pathname}${location.search}`}</output>
}

function RouteChangeButton() {
  const navigate = useNavigate()
  return (
    <button type="button" onClick={() => navigate('/discover')}>
      前往探索
    </button>
  )
}

function renderNavigation(
  unread: HomeFeed['unread'] = { messages: 0, notifications: 0 },
  initialEntry = '/home',
  onRefreshHome?: () => void,
) {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Navbar unread={unread} onRefreshHome={onRefreshHome} />
      <LocationProbe />
      <RouteChangeButton />
      <Routes>
        <Route path="/login" element={<h1>登录页面</h1>} />
        <Route path="*" element={null} />
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  useAuthStore.getState().setAuth('test-token', user)
})

afterEach(() => {
  cleanup()
  useAuthStore.getState().logout()
  window.localStorage.clear()
})

describe('responsive application navigation', () => {
  it('renders the approved desktop order with only three primary links', () => {
    renderNavigation({ messages: 2, notifications: 3 })

    expect(
      within(screen.getByLabelText('桌面端主导航'))
        .getAllByRole('link')
        .map((link) => link.textContent),
    ).toEqual(['首页', '探索', '发布'])

    const header = screen.getByLabelText('桌面端应用导航')
    expect(
      within(header)
        .getAllByRole('link')
        .map((link) => link.getAttribute('aria-label') || link.textContent),
    ).toEqual([
      'CampusMate 首页',
      '首页',
      '探索',
      '发布',
      '消息，2 条未读',
      '通知，3 条未读',
      '教程',
    ])
  })

  it('announces exact unread counts, caps visual badges, and omits zero badges', () => {
    renderNavigation({ messages: 125, notifications: 0 })

    const messages = screen.getByLabelText('消息，125 条未读')
    expect(within(messages).getByText('99+')).not.toBeNull()

    const notifications = screen.getByLabelText('通知，0 条未读')
    expect(within(notifications).queryByText('0')).toBeNull()
  })

  it('opens the complete menu and uses matched profile destinations', () => {
    renderNavigation()
    fireEvent.click(screen.getByRole('button', { name: '打开个人菜单' }))

    const menu = screen.getByRole('menu', { name: '个人菜单' })
    const items = within(menu).getAllByRole('menuitem')
    expect(items.map((item) => item.textContent)).toEqual([
      '我的活动',
      '我的小组',
      '查看个人主页',
      '设置',
      '退出登录',
    ])
    expect(items.slice(0, 4).map((item) => item.getAttribute('href'))).toEqual([
      '/profile?tab=events',
      '/profile?tab=groups',
      '/profile?view=public',
      '/profile?view=settings',
    ])
  })

  it('opens from the keyboard, moves menu focus, and restores trigger focus on Escape', async () => {
    renderNavigation()
    const trigger = screen.getByRole('button', { name: '打开个人菜单' })

    trigger.focus()
    fireEvent.keyDown(trigger, { key: 'ArrowDown' })

    const firstItem = await screen.findByRole('menuitem', { name: '我的活动' })
    const secondItem = screen.getByRole('menuitem', { name: '我的小组' })
    await waitFor(() => expect(document.activeElement).toBe(firstItem))

    fireEvent.keyDown(firstItem, { key: 'ArrowDown' })
    expect(document.activeElement).toBe(secondItem)

    fireEvent.keyDown(secondItem, { key: 'Escape' })
    expect(screen.queryByRole('menu')).toBeNull()
    expect(document.activeElement).toBe(trigger)
  })

  it('focuses the first menu item when Enter opens the trigger', async () => {
    renderNavigation()
    const trigger = screen.getByRole('button', { name: '打开个人菜单' })

    trigger.focus()
    fireEvent.keyDown(trigger, { key: 'Enter' })

    const firstItem = await screen.findByRole('menuitem', { name: '我的活动' })
    await waitFor(() => expect(document.activeElement).toBe(firstItem))
  })

  it('closes the menu after an outside click', () => {
    renderNavigation()
    fireEvent.click(screen.getByRole('button', { name: '打开个人菜单' }))
    expect(screen.getByRole('menu')).not.toBeNull()

    fireEvent.mouseDown(document.body)

    expect(screen.queryByRole('menu')).toBeNull()
  })

  it('closes the menu after a route change', () => {
    renderNavigation()
    fireEvent.click(screen.getByRole('button', { name: '打开个人菜单' }))

    fireEvent.click(screen.getByRole('button', { name: '前往探索' }))

    expect(screen.getByLabelText('当前位置').textContent).toContain('/discover')
    expect(screen.queryByRole('menu')).toBeNull()
  })

  it('closes on menu activation and logs out to the login route', async () => {
    renderNavigation()
    fireEvent.click(screen.getByRole('button', { name: '打开个人菜单' }))

    fireEvent.click(screen.getByRole('menuitem', { name: '退出登录' }))

    expect(await screen.findByRole('heading', { name: '登录页面' })).not.toBeNull()
    expect(useAuthStore.getState()).toMatchObject({
      token: null,
      user: null,
      isAuthenticated: false,
    })
    expect(screen.queryByRole('menu')).toBeNull()
  })

  it('keeps the mobile navigation to five stable cells with a safe-area bar', () => {
    renderNavigation()

    const mobile = screen.getByLabelText('移动端主导航')
    expect(within(mobile).getAllByRole('link').map((link) => link.textContent)).toEqual([
      '首页',
      '探索',
      '发布',
      '消息',
      '我的',
    ])
    expect(mobile.className).toContain('pb-[env(safe-area-inset-bottom)]')
    expect(
      within(mobile).getByRole('link', { name: '发布' }).getAttribute('data-primary-action'),
    ).toBe('true')
  })

  it('refreshes the shared home request when the active home link is selected', () => {
    const onRefreshHome = vi.fn()
    renderNavigation({ messages: 0, notifications: 0 }, '/home', onRefreshHome)

    fireEvent.click(
      within(screen.getByLabelText('桌面端主导航')).getByRole('link', { name: '首页' }),
    )

    expect(onRefreshHome).toHaveBeenCalledOnce()
  })
})

describe('authenticated application shell', () => {
  it('shares one aggregate request between navigation badges and routed content', async () => {
    vi.mocked(getHomeFeed).mockResolvedValue(feed)

    function FeedConsumer() {
      const { feed: currentFeed } = useHomeFeed()
      return <p>{currentFeed ? `首页读取 ${currentFeed.unread.messages}` : '首页加载中'}</p>
    }

    render(
      <MemoryRouter initialEntries={['/home']}>
        <Routes>
          <Route path="/" element={<MainLayout />}>
            <Route path="home" element={<FeedConsumer />} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByText('首页读取 2')).not.toBeNull()
    expect(screen.getByLabelText('消息，2 条未读')).not.toBeNull()
    expect(screen.getByLabelText('通知，3 条未读')).not.toBeNull()
    expect(getHomeFeed).toHaveBeenCalledOnce()
  })
})
