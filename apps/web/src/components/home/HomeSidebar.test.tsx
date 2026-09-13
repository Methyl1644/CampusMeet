// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import type {
  HomeDeadlineReminder,
  HomeJoinedGroup,
  HomeProfile,
  HomeTopic,
} from '@shared/types'
import DeadlineReminder from './DeadlineReminder'
import MyEventsSummary from './MyEventsSummary'
import MyGroupsSummary from './MyGroupsSummary'
import ProfileSummary from './ProfileSummary'

const profile: HomeProfile = {
  id: 'student-1',
  nickname: '林晓',
  avatar: null,
  major: '软件工程',
  grade: '2024级',
}

const attending: HomeTopic[] = [
  {
    id: 'topic-attending',
    channel: 'official',
    title: '南京大学创新创业训练计划',
    short_title: '创新训练计划',
    organizer: '创新创业学院',
    edition: '2026 秋季',
    summary: '面向全校学生的创新项目。',
    content: '活动详情',
    source_url: null,
    source_status: 'verified',
    cover_url: '/images/innovation.jpg',
    follower_count: 42,
    followed: true,
    tags: [],
    status: 'active',
    trust_badges: [],
    responsible_people: [],
    registration_deadline: '2026-09-16T12:00:00+08:00',
    activity_start_at: '2026-09-20T09:00:00+08:00',
    activity_end_at: null,
  },
]

const saved: HomeTopic[] = [
  {
    ...attending[0],
    id: 'topic-saved',
    title: '紫金山校园定向赛',
    short_title: '校园定向赛',
    organizer: '学生体育协会',
    cover_url: null,
  },
]

const joinedGroups: HomeJoinedGroup[] = [
  {
    id: 'team-1',
    post_id: 'post-1',
    activity_name: '美赛建模小组',
    member_role: 'member',
    created_at: '2026-09-10T08:00:00+08:00',
    current_members: 3,
    target_members: 4,
  },
]

const reminder: HomeDeadlineReminder = {
  ...attending[0],
  id: 'topic-deadline',
  title: '全国大学生数学建模竞赛',
  days_remaining: 3,
}

function renderWithRouter(node: React.ReactNode) {
  return render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      {node}
    </MemoryRouter>,
  )
}

afterEach(cleanup)

describe('ProfileSummary', () => {
  it('shows the avatar fallback, identity details, and profile destination', () => {
    renderWithRouter(<ProfileSummary profile={profile} />)

    expect(screen.getByRole('img', { name: '林晓的头像' }).textContent).toBe('林')
    expect(screen.getByText('林晓')).toBeTruthy()
    expect(screen.getByText('软件工程 · 2024级')).toBeTruthy()
    expect(screen.getByRole('link', { name: '查看个人主页' }).getAttribute('href')).toBe('/profile')
  })
})

describe('MyEventsSummary', () => {
  it('switches between attending and saved events with accessible controlled tabs', () => {
    renderWithRouter(<MyEventsSummary attending={attending} saved={saved} />)

    const attendingTab = screen.getByRole('tab', { name: '参加中' })
    const savedTab = screen.getByRole('tab', { name: '已收藏' })
    const panel = screen.getByRole('tabpanel')

    expect(attendingTab.getAttribute('aria-selected')).toBe('true')
    expect(attendingTab.getAttribute('aria-controls')).toBe(panel.id)
    expect(savedTab.getAttribute('aria-controls')).not.toBe(panel.id)
    expect(panel.style.minHeight).toBe('8.5rem')
    expect(screen.getByText(attending[0].title)).toBeTruthy()

    fireEvent.click(savedTab)

    expect(savedTab.getAttribute('aria-selected')).toBe('true')
    expect(savedTab.getAttribute('aria-controls')).toBe(screen.getByRole('tabpanel').id)
    expect(screen.queryByText(attending[0].title)).toBeNull()
    expect(screen.getByText(saved[0].title)).toBeTruthy()
    expect(screen.getByRole('link', { name: '查看全部活动' }).getAttribute('href')).toBe(
      '/profile?tab=events',
    )
  })

  it('supports arrow-key tab selection without changing the summary geometry', () => {
    renderWithRouter(<MyEventsSummary attending={attending} saved={saved} />)

    const attendingTab = screen.getByRole('tab', { name: '参加中' })
    const savedTab = screen.getByRole('tab', { name: '已收藏' })
    fireEvent.keyDown(attendingTab, { key: 'ArrowRight' })

    expect(savedTab.getAttribute('aria-selected')).toBe('true')
    expect(savedTab.getAttribute('tabindex')).toBe('0')
    expect(screen.getByRole('tabpanel').style.minHeight).toBe('8.5rem')
  })

  it('links an empty event tab directly to event discovery', () => {
    renderWithRouter(<MyEventsSummary attending={[]} saved={saved} />)

    expect(screen.getByText('还没有参加的活动')).toBeTruthy()
    expect(screen.getByRole('link', { name: '探索活动' }).getAttribute('href')).toBe(
      '/discover?view=activity',
    )
  })

  it('keeps the saved tab accessible when only attending events are degraded', () => {
    renderWithRouter(
      <MyEventsSummary attending={[]} saved={saved} attendingDegraded savedDegraded={false} />,
    )

    const attendingTab = screen.getByRole('tab', { name: '参加中' })
    const savedTab = screen.getByRole('tab', { name: '已收藏' })
    expect(attendingTab.getAttribute('aria-selected')).toBe('true')
    expect(screen.getByRole('status').textContent).toBe('参加中的活动暂时无法加载')

    fireEvent.click(savedTab)

    expect(savedTab.getAttribute('aria-selected')).toBe('true')
    expect(screen.getByRole('tabpanel').getAttribute('aria-labelledby')).toBe(savedTab.id)
    expect(screen.getByText(saved[0].title)).toBeTruthy()
    expect(screen.queryByText(attending[0].title)).toBeNull()
  })

  it('keeps the attending tab visible when only saved events are degraded', () => {
    renderWithRouter(
      <MyEventsSummary attending={attending} saved={[]} attendingDegraded={false} savedDegraded />,
    )

    const attendingTab = screen.getByRole('tab', { name: '参加中' })
    const savedTab = screen.getByRole('tab', { name: '已收藏' })
    expect(screen.getByText(attending[0].title)).toBeTruthy()

    fireEvent.click(savedTab)

    expect(savedTab.getAttribute('aria-selected')).toBe('true')
    expect(screen.getByRole('tabpanel').getAttribute('aria-labelledby')).toBe(savedTab.id)
    expect(screen.getByRole('status').textContent).toBe('已收藏的活动暂时无法加载')
    expect(screen.queryByText(attending[0].title)).toBeNull()
    expect(attendingTab.getAttribute('aria-controls')).not.toBe(screen.getByRole('tabpanel').id)
  })
})

describe('MyGroupsSummary', () => {
  it('shows one joined group and links to the complete groups view', () => {
    renderWithRouter(<MyGroupsSummary groups={joinedGroups} />)

    expect(screen.getByText('美赛建模小组')).toBeTruthy()
    expect(screen.getByText('3 / 4 人')).toBeTruthy()
    expect(screen.getByRole('link', { name: '美赛建模小组' }).getAttribute('href')).toBe(
      '/teams/team-1',
    )
    expect(screen.getByRole('link', { name: '查看全部小组' }).getAttribute('href')).toBe(
      '/profile?tab=groups',
    )
  })

  it('links an empty group summary directly to group discovery', () => {
    renderWithRouter(<MyGroupsSummary groups={[]} />)

    expect(screen.getByText('还没有加入小组')).toBeTruthy()
    expect(screen.getByRole('link', { name: '探索小组' }).getAttribute('href')).toBe(
      '/discover?view=group',
    )
  })
})

describe('DeadlineReminder', () => {
  it('renders nothing for a missing reminder', () => {
    const { container } = renderWithRouter(<DeadlineReminder reminder={null} />)

    expect(container.innerHTML).toBe('')
    expect(screen.queryByRole('status')).toBeNull()
  })

  it('shows deadline details and an icon-only named close control', () => {
    renderWithRouter(<DeadlineReminder reminder={reminder} />)

    expect(screen.getByRole('status').textContent).toContain('距报名截止还有 3 天')
    expect(screen.getByText(reminder.title)).toBeTruthy()
    expect(screen.getByRole('link', { name: '查看活动' }).getAttribute('href')).toBe(
      '/topics/topic-deadline',
    )
    const close = screen.getByRole('button', { name: '关闭截止提醒' })
    expect(close.getAttribute('title')).toBe('关闭截止提醒')
    expect(close.textContent).toBe('')
  })

  it('keeps dismissal local to the mounted component', () => {
    const first = renderWithRouter(<DeadlineReminder reminder={reminder} />)

    fireEvent.click(screen.getByRole('button', { name: '关闭截止提醒' }))
    expect(screen.queryByRole('status')).toBeNull()

    first.unmount()
    renderWithRouter(<DeadlineReminder reminder={reminder} />)
    expect(screen.getByRole('status')).toBeTruthy()
  })
})
