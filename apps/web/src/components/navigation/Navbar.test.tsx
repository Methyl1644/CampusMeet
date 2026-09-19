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
  attending_topics: [],
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
      '梧桐遇首页',
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

    const header = screen.getByLabelText('桌面端应用导航')
    const messages = within(header).getByLabelText('消息，125 条未读')
    expect(within(messages).getByText('99+')).not.toBeNull()

    const notifications = within(header).getByLabelText('通知，0 条未读')
    expect(within(notifications).queryByText('0')).toBeNull()
  })

  it('opens the complete menu and uses matched profile destinations', () => {
    renderNavigation()
    fireEvent.click(screen.getByRole('button', { name: '打开个人菜单' }))

    const menu = screen.getByRole('menu', { name: '个人菜单' })
    const items = within(menu).getAllByRole('menuitem')
    expect(items.map((item) => item.textContent)).toEqual([
      '我的活动',
      '我的组队与发布',
      '查看个人主页',
      '我的授权',
      '设置',
      '退出登录',
    ])
    expect(items.slice(0, 5).map((item) => item.getAttribute('href'))).toEqual([
      '/my/activities',
      '/my/groups',
      '/users/me',
      '/authorizations',
      '/settings',
    ])
  })

  it('opens from the keyboard, moves menu focus, and restores trigger focus on Escape', async () => {
    renderNavigation()
    const trigger = screen.getByRole('button', { name: '打开个人菜单' })

    trigger.focus()
    fireEvent.keyDown(trigger, { key: 'ArrowDown' })

    const firstItem = await screen.findByRole('menuitem', { name: '我的活动' })
    const secondItem = screen.getByRole('menuitem', { name: '我的组队与发布' })
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

  it('focuses the last menu item when ArrowUp opens the trigger', async () => {
    renderNavigation()
    const trigger = screen.getByRole('button', { name: '打开个人菜单' })

    trigger.focus()
    fireEvent.keyDown(trigger, { key: 'ArrowUp' })

    const lastItem = await screen.findByRole('menuitem', { name: '退出登录' })
    await waitFor(() => expect(document.activeElement).toBe(lastItem))
  })

  it('activates a focused link menu item with Space', async () => {
    renderNavigation()
    const trigger = screen.getByRole('button', { name: '打开个人菜单' })

    trigger.focus()
    fireEvent.keyDown(trigger, { key: 'ArrowDown' })
    const firstItem = await screen.findByRole('menuitem', { name: '我的活动' })
    await waitFor(() => expect(document.activeElement).toBe(firstItem))

    fireEvent.keyDown(firstItem, { key: ' ' })

    expect(screen.getByLabelText('当前位置').textContent).toBe('/my/activities')
    expect(screen.queryByRole('menu')).toBeNull()
  })

  it.each([
    { direction: 'Tab', shiftKey: false },
    { direction: 'Shift+Tab', shiftKey: true },
  ])('closes the menu when $direction leaves it', async ({ shiftKey }) => {
    renderNavigation()
    const trigger = screen.getByRole('button', { name: '打开个人菜单' })

    trigger.focus()
    fireEvent.keyDown(trigger, { key: 'ArrowDown' })
    const firstItem = await screen.findByRole('menuitem', { name: '我的活动' })
    await waitFor(() => expect(document.activeElement).toBe(firstItem))

    fireEvent.keyDown(firstItem, { key: 'Tab', shiftKey })

    expect(screen.queryByRole('menu')).toBeNull()
  })

  it('closes a click-opened menu when Shift+Tab leaves the trigger', () => {
    renderNavigation()
    const trigger = screen.getByRole('button', { name: '打开个人菜单' })

    fireEvent.click(trigger)
    expect(screen.getByRole('menu', { name: '个人菜单' })).not.toBeNull()

    fireEvent.keyDown(trigger, { key: 'Tab', shiftKey: true })

    expect(screen.queryByRole('menu')).toBeNull()
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
    const bar = mobile.firstElementChild
    expect(bar?.children).toHaveLength(5)
    expect(within(mobile).getAllByRole('link').map((link) => link.textContent)).toEqual([
      '首页',
      '探索',
      '发布',
      '消息',
    ])
    expect(within(mobile).getByRole('button', { name: '打开我的菜单' })).not.toBeNull()
    expect(mobile.className).toContain('pb-[env(safe-area-inset-bottom)]')
    expect(
      within(mobile).getByRole('link', { name: '发布' }).getAttribute('data-primary-action'),
    ).toBe('true')
  })

  it('exposes notifications, tutorial, and matched profile destinations from mobile 我的', () => {
    renderNavigation({ messages: 0, notifications: 3 })

    fireEvent.click(
      within(screen.getByLabelText('移动端主导航')).getByRole('button', {
        name: '打开我的菜单',
      }),
    )

    const menu = screen.getByRole('menu', { name: '我的菜单' })
    const items = within(menu).getAllByRole('menuitem')
    expect(items.map((item) => item.textContent)).toEqual([
      '通知',
      '教程',
      '我的活动',
      '我的组队与发布',
      '查看个人主页',
      '我的授权',
      '设置',
      '退出登录',
    ])
    expect(items.slice(0, 7).map((item) => item.getAttribute('href'))).toEqual([
      '/notifications',
      '/tutorial',
      '/my/activities',
      '/my/groups',
      '/users/me',
      '/authorizations',
      '/settings',
    ])
  })

  it.each([
    { count: 7, badge: '7' },
    { count: 125, badge: '99+' },
    { count: 0, badge: null },
  ])('announces $count mobile unread messages with badge $badge', ({ count, badge }) => {
    renderNavigation({ messages: count, notifications: 0 })

    const messages = within(screen.getByLabelText('移动端主导航')).getByRole('link', {
      name: `消息，${count} 条未读`,
    })
    if (badge) {
      expect(within(messages).getByText(badge)).not.toBeNull()
    } else {
      expect(within(messages).queryByText('0')).toBeNull()
    }
  })

  it('refreshes the shared home request when the active home link is selected', () => {
    const onRefreshHome = vi.fn()
    renderNavigation({ messages: 0, notifications: 0 }, '/home', onRefreshHome)

    fireEvent.click(
      within(screen.getByLabelText('桌面端主导航')).getByRole('link', { name: '首页' }),
    )

    expect(onRefreshHome).toHaveBeenCalledOnce()
  })

  it('shows the management center only to users with management scope', () => {
    useAuthStore.getState().setAuth('test-token', {
      ...user,
      identity: {
        campus_verified: true,
        platform_role: 'operator',
        organization_roles: [],
        topic_roles: [],
        post_roles: [],
      },
    })
    renderNavigation()

    fireEvent.click(screen.getByRole('button', { name: '打开个人菜单' }))
    const link = within(screen.getByRole('menu', { name: '个人菜单' })).getByRole('menuitem', {
      name: '管理中心',
    })
    expect(link.getAttribute('href')).toBe('/management')
  })
})

describe('authenticated application shell', () => {
  it('announces degraded unread counts without presenting false zeroes and retries them', async () => {
    vi.mocked(getHomeFeed).mockResolvedValue({ ...feed, unread: { messages: 0, notifications: 0 }, warnings: ['unread'] })

    render(
      <MemoryRouter initialEntries={['/home']}>
        <Routes>
          <Route path="/" element={<MainLayout />}>
            <Route path="home" element={<p>首页</p>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )

    const desktop = screen.getByLabelText('桌面端应用导航')
    expect(await within(desktop).findByLabelText('消息，未读数暂不可用')).not.toBeNull()
    expect(within(desktop).getByLabelText('通知，未读数暂不可用')).not.toBeNull()
    expect(within(desktop).getByLabelText('消息，未读数暂不可用').getAttribute('href')).toBe('/messages')
    const mobile = screen.getByLabelText('移动端主导航')
    expect(within(mobile).getByLabelText('消息，未读数暂不可用').getAttribute('href')).toBe('/messages')
    expect(within(mobile).getByRole('button', { name: '重新加载未读数' })).not.toBeNull()
    fireEvent.click(within(desktop).getByRole('button', { name: '重新加载未读数' }))
    await waitFor(() => expect(getHomeFeed).toHaveBeenCalledTimes(2))
  })

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
    expect(
      within(screen.getByLabelText('桌面端应用导航')).getByLabelText('消息，2 条未读'),
    ).not.toBeNull()
    expect(
      within(screen.getByLabelText('移动端主导航')).getByLabelText('消息，2 条未读'),
    ).not.toBeNull()
    expect(
      within(screen.getByLabelText('桌面端应用导航')).getByLabelText('通知，3 条未读'),
    ).not.toBeNull()
    expect(getHomeFeed).toHaveBeenCalledOnce()
  })
})
