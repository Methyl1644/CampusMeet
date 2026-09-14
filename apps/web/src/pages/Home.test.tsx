// @vitest-environment jsdom

import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import type { HomeFeed, RecommendedHomeTopic } from '@shared/types'
import { getHomeFeed } from '@/api/home'
import GroupTimeline from '@/components/home/GroupTimeline'
import { HomeFeedProvider } from '@/features/home/HomeFeedContext'
import Home from './Home'

vi.mock('@/api/home', () => ({
  getHomeFeed: vi.fn(),
}))

vi.mock('@/components/DiscoveryHub', () => ({
  default: () => <div>旧首页</div>,
}))

function localIso(dayOffset: number, hour: number) {
  const value = new Date()
  value.setHours(hour, 0, 0, 0)
  value.setDate(value.getDate() + dayOffset)
  return value.toISOString()
}

const recommendedTopic: RecommendedHomeTopic = {
  id: 'topic-ai-contest',
  channel: 'official',
  title: '校园人工智能创新挑战赛',
  short_title: '人工智能挑战赛',
  organizer: '计算机科学与技术系',
  edition: '2026 秋季',
  summary: '面向全校学生的人工智能创新实践。',
  content: '活动详情',
  source_url: null,
  source_status: 'verified',
  cover_url: '/images/ai-contest.jpg',
  follower_count: 128,
  followed: true,
  tags: [],
  status: 'active',
  trust_badges: [],
  responsible_people: [],
  registration_deadline: localIso(2, 18),
  activity_start_at: localIso(8, 9),
  activity_end_at: null,
  recommendation_reason: '与你的人工智能兴趣相关',
}

const attendingTopic = {
  ...recommendedTopic,
  id: 'topic-attending-workshop',
  title: '软件工程实践工作坊',
}

const feedFixture: HomeFeed = {
  profile: {
    id: 'student-1',
    nickname: '林晓',
    avatar: null,
    major: '软件工程',
    grade: '2024级',
  },
  deadline_reminder: {
    ...recommendedTopic,
    id: 'topic-deadline',
    title: '全国大学生数学建模竞赛',
    days_remaining: 2,
  },
  recommended_topics: [
    recommendedTopic,
    {
      ...recommendedTopic,
      id: 'topic-volunteer',
      title: '秋季校园志愿服务周',
      cover_url: null,
      followed: false,
      follower_count: 46,
      recommendation_reason: '近期校园热门活动',
    },
  ],
  attending_topics: [attendingTopic],
  followed_topics: [recommendedTopic],
  joined_groups: [
    {
      id: 'team-modeling',
      post_id: 'post-modeling',
      activity_name: '美赛建模小组',
      member_role: 'member',
      created_at: localIso(-2, 10),
      current_members: 3,
      target_members: 4,
    },
  ],
  group_timeline: [
    {
      team_id: 'team-modeling',
      team_name: '美赛建模小组',
      task_id: 'task-paper',
      title: '完成论文框架',
      due_at: localIso(0, 20),
      done: false,
    },
    {
      team_id: 'team-modeling',
      team_name: '美赛建模小组',
      task_id: 'task-data',
      title: '整理训练数据',
      due_at: localIso(0, 22),
      done: true,
    },
    {
      team_id: 'team-modeling',
      team_name: '美赛建模小组',
      task_id: 'task-review',
      title: '交叉检查模型结果',
      due_at: localIso(1, 19),
      done: false,
    },
  ],
  unread: { messages: 2, notifications: 1 },
  warnings: [],
}

function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise
    reject = rejectPromise
  })
  return { promise, resolve, reject }
}

function renderHome() {
  return render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <HomeFeedProvider>
        <Home />
      </HomeFeedProvider>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('Home', () => {
  it('uses attending topics in the summary and exposes one page-level heading', async () => {
    vi.mocked(getHomeFeed).mockResolvedValue(feedFixture)

    renderHome()

    expect(await screen.findByRole('heading', { level: 1, name: '你的梧桐遇首页' })).toBeTruthy()
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1)
    expect(screen.getByRole('tabpanel').textContent).toContain(attendingTopic.title)
  })

  it('keeps timeline rows distinct when two teams share a task id across a rerender', () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined)
    const sharedDueAt = localIso(0, 20)
    const initialItems = [
      {
        team_id: 'team-modeling',
        team_name: '美赛建模小组',
        task_id: 't1',
        title: '完成论文框架',
        due_at: sharedDueAt,
        done: false,
      },
      {
        team_id: 'team-robotics',
        team_name: '机器人竞赛小组',
        task_id: 't1',
        title: '测试巡线模块',
        due_at: sharedDueAt,
        done: false,
      },
      {
        team_id: '',
        team_name: '旧版数据小组甲',
        task_id: '',
        title: '整理旧版资料',
        due_at: sharedDueAt,
        done: false,
      },
      {
        team_id: '',
        team_name: '旧版数据小组乙',
        task_id: '',
        title: '核对旧版资料',
        due_at: sharedDueAt,
        done: false,
      },
    ]

    try {
      const { rerender } = render(
        <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <GroupTimeline items={initialItems} />
        </MemoryRouter>,
      )

      expect(screen.getByRole('link', { name: /完成论文框架/ }).getAttribute('href')).toBe('/teams/team-modeling')
      expect(screen.getByRole('link', { name: /测试巡线模块/ }).getAttribute('href')).toBe('/teams/team-robotics')

      rerender(
        <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <GroupTimeline
            items={[
              initialItems[0],
              { ...initialItems[1], title: '完成巡线模块复测', done: true },
              initialItems[2],
              { ...initialItems[3], title: '完成旧版资料核对', done: true },
            ]}
          />
        </MemoryRouter>,
      )

      expect(screen.queryByText('测试巡线模块')).toBeNull()
      expect(screen.getByRole('link', { name: /完成巡线模块复测/ }).getAttribute('href')).toBe('/teams/team-robotics')
      expect(consoleError.mock.calls.some((call) => call.some((value) => String(value).includes('same key')))).toBe(false)
    } finally {
      consoleError.mockRestore()
    }
  })

  it('preserves a legacy timeline row identity when empty-id tasks are inserted and reordered', () => {
    const sharedDueAt = localIso(0, 20)
    const targetItem = {
      team_id: '',
      team_name: '旧版数据小组甲',
      task_id: '',
      title: '整理旧版资料',
      due_at: sharedDueAt,
      done: false,
    }
    const otherItem = {
      team_id: '',
      team_name: '旧版数据小组乙',
      task_id: '',
      title: '核对旧版资料',
      due_at: sharedDueAt,
      done: false,
    }
    const insertedItem = {
      team_id: '',
      team_name: '旧版数据小组丙',
      task_id: '',
      title: '归档旧版资料',
      due_at: sharedDueAt,
      done: false,
    }
    const { rerender } = render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <GroupTimeline items={[targetItem, otherItem]} />
      </MemoryRouter>,
    )
    const targetRow = screen.getByRole('link', { name: /整理旧版资料/ }).closest('li')

    rerender(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <GroupTimeline items={[insertedItem, targetItem, otherItem]} />
      </MemoryRouter>,
    )

    expect(screen.getByRole('link', { name: /整理旧版资料/ }).closest('li')).toBe(targetRow)

    rerender(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <GroupTimeline items={[otherItem, insertedItem, targetItem]} />
      </MemoryRouter>,
    )

    expect(screen.getByRole('link', { name: /整理旧版资料/ }).closest('li')).toBe(targetRow)
  })

  it('gives genuinely identical legacy timeline rows distinct keys', () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined)
    const legacyItem = {
      team_id: '',
      team_name: '旧版数据小组',
      task_id: '',
      title: '整理旧版资料',
      due_at: localIso(0, 20),
      done: false,
    }

    try {
      render(
        <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <GroupTimeline items={[legacyItem, { ...legacyItem }]} />
        </MemoryRouter>,
      )

      expect(consoleError.mock.calls.some((call) => call.some((value) => String(value).includes('same key')))).toBe(false)
    } finally {
      consoleError.mockRestore()
    }
  })

  it('renders personalized recommendations and a locally grouped joined-group timeline', async () => {
    vi.mocked(getHomeFeed).mockResolvedValue(feedFixture)

    renderHome()

    expect(await screen.findByRole('heading', { name: '为你推荐' })).toBeTruthy()
    expect(screen.getByText(recommendedTopic.title)).toBeTruthy()
    expect(screen.getByText(recommendedTopic.recommendation_reason)).toBeTruthy()
    expect(screen.getByRole('link', { name: new RegExp(recommendedTopic.title) }).getAttribute('href')).toBe(
      '/topics/topic-ai-contest',
    )
    expect(screen.queryByRole('button', { name: `收藏${recommendedTopic.title}` })).toBeNull()

    expect(screen.getByRole('heading', { name: '来自我的小组' })).toBeTruthy()
    expect(screen.getAllByRole('heading', { name: '今天' })).toHaveLength(1)
    expect(screen.getByRole('heading', { name: '明天' })).toBeTruthy()
    expect(screen.getByRole('link', { name: /完成论文框架/ }).getAttribute('href')).toBe(
      '/teams/team-modeling',
    )
    expect(screen.getByText('已完成')).toBeTruthy()
    expect(getHomeFeed).toHaveBeenCalledOnce()
  })

  it('gates event-card translation behind the reduced-motion-safe media variant', async () => {
    vi.stubGlobal('matchMedia', vi.fn().mockReturnValue({ matches: true }))
    vi.mocked(getHomeFeed).mockResolvedValue(feedFixture)

    renderHome()

    const card = await screen.findByRole('link', { name: new RegExp(recommendedTopic.title) })
    expect(window.matchMedia('(prefers-reduced-motion: reduce)').matches).toBe(true)
    expect(card.classList.contains('motion-safe:hover:-translate-y-0.5')).toBe(true)
    expect(card.classList.contains('hover:-translate-y-0.5')).toBe(false)
  })

  it('keeps valid long recommendation content inside stable card geometry', async () => {
    const longReason = '与你关注的人工智能、机器人、跨学科创新、产品设计和校园公益方向高度相关，也符合你近期希望参与长期项目并认识不同专业同学的偏好'
    const longTopic: RecommendedHomeTopic = {
      ...recommendedTopic,
      id: 'topic-long-content',
      title: '跨学科校园人工智能与机器人创新实践挑战赛长期联合招募计划',
      organizer: '计算机科学与技术系、电子科学与工程学院及创新创业学院联合工作组',
      recommendation_reason: longReason,
    }
    vi.mocked(getHomeFeed).mockResolvedValue({
      ...feedFixture,
      deadline_reminder: null,
      recommended_topics: [longTopic],
    })

    renderHome()

    const card = await screen.findByRole('link', { name: new RegExp(longTopic.title) })
    const body = card.lastElementChild as HTMLElement
    const timing = within(card).getByLabelText(/截止/)
    const reason = within(card).getByText(longReason)

    expect(card.classList.contains('h-[392px]')).toBe(true)
    expect(body.classList.contains('h-[238px]')).toBe(true)
    expect(timing.classList.contains('line-clamp-2')).toBe(true)
    expect(timing.getAttribute('title')).toBe(timing.textContent)
    expect(reason.classList.contains('line-clamp-2')).toBe(true)
    expect(reason.textContent).toBe(longReason)
  })

  it('renders restrained recommendation and timeline empty states', async () => {
    vi.mocked(getHomeFeed).mockResolvedValue({
      ...feedFixture,
      deadline_reminder: null,
      recommended_topics: [],
      followed_topics: [],
      joined_groups: [],
      group_timeline: [],
    })

    renderHome()

    expect(await screen.findByText('暂时没有新的活动推荐')).toBeTruthy()
    const recommendations = screen.getByRole('heading', { name: '为你推荐' }).closest('section')
    expect(recommendations?.previousElementSibling).toBeNull()
    expect(within(recommendations as HTMLElement).getByRole('link', { name: '探索活动' }).getAttribute('href')).toBe(
      '/discover?view=activity',
    )
    expect(screen.getByText('小组有新任务时，会在这里按日期出现。')).toBeTruthy()
    expect(screen.getByRole('link', { name: '探索组队' }).getAttribute('href')).toBe(
      '/discover?view=group',
    )
  })

  it('keeps healthy recommendations visible when the group timeline is degraded', async () => {
    vi.mocked(getHomeFeed).mockResolvedValue({
      ...feedFixture,
      group_timeline: [],
      warnings: ['group_timeline'],
    })

    renderHome()

    expect(await screen.findByText(recommendedTopic.title)).toBeTruthy()
    expect(screen.getByText('小组动态暂时无法加载')).toBeTruthy()
    expect(screen.queryByText('小组有新任务时，会在这里按日期出现。')).toBeNull()
  })

  it('keeps saved events selectable when attending events are degraded', async () => {
    vi.mocked(getHomeFeed).mockResolvedValue({
      ...feedFixture,
      attending_topics: [],
      warnings: ['attending_topics'],
    })

    renderHome()

    expect(await screen.findByText('参加中的活动暂时无法加载')).toBeTruthy()
    fireEvent.click(screen.getByRole('tab', { name: '已收藏' }))
    expect(within(screen.getByRole('tabpanel')).getByText(recommendedTopic.title)).toBeTruthy()
  })

  it('keeps attending events visible when saved events are degraded', async () => {
    vi.mocked(getHomeFeed).mockResolvedValue({
      ...feedFixture,
      followed_topics: [],
      warnings: ['followed_topics'],
    })

    renderHome()

    expect(await screen.findByText(attendingTopic.title)).toBeTruthy()
    fireEvent.click(screen.getByRole('tab', { name: '已收藏' }))
    expect(screen.getByText('已收藏的活动暂时无法加载')).toBeTruthy()
  })

  it('distinguishes an unavailable deadline reminder from a healthy empty result', async () => {
    vi.mocked(getHomeFeed).mockResolvedValue({
      ...feedFixture,
      warnings: ['deadline_reminder'],
    })

    renderHome()

    expect(await screen.findByText('截止提醒暂时无法加载')).toBeTruthy()
    expect(screen.getByText(recommendedTopic.title)).toBeTruthy()
    expect(screen.queryByText(/距报名截止还有/)).toBeNull()
    expect(screen.queryByRole('button', { name: '关闭截止提醒' })).toBeNull()
    expect(screen.queryByRole('link', { name: '查看活动' })).toBeNull()
  })

  it('offers one focused retry after a fatal aggregate error', async () => {
    vi.mocked(getHomeFeed)
      .mockRejectedValueOnce(new Error('offline'))
      .mockResolvedValueOnce(feedFixture)

    renderHome()

    fireEvent.click(await screen.findByRole('button', { name: '重新加载首页' }))

    expect(await screen.findByText(feedFixture.profile.nickname)).toBeTruthy()
    expect(screen.queryByRole('button', { name: '重新加载首页' })).toBeNull()
    expect(getHomeFeed).toHaveBeenCalledTimes(2)
  })

  it('reserves representative page and card geometry while loading', () => {
    const request = deferred<HomeFeed>()
    vi.mocked(getHomeFeed).mockReturnValue(request.promise)

    renderHome()

    const loading = screen.getByRole('status', { name: '正在加载首页' })
    expect(loading.className).toContain('lg:gap-10')
    expect(within(loading).getByTestId('home-skeleton-sidebar').className).toContain('min-h')
    const eventSkeleton = within(loading).getAllByTestId('home-skeleton-event')[0]
    expect(eventSkeleton.className).toContain('w-[272px]')
    expect(eventSkeleton.className).toContain('h-[392px]')
    expect(within(loading).getByTestId('home-skeleton-timeline').className).toContain('min-h')
  })

  it('uses native scrolling controls whose state follows the rail boundaries', async () => {
    vi.mocked(getHomeFeed).mockResolvedValue(feedFixture)
    renderHome()

    const rail = await screen.findByRole('list', { name: '推荐活动' })
    Object.defineProperties(rail, {
      clientWidth: { configurable: true, value: 640 },
      scrollWidth: { configurable: true, value: 1200 },
      scrollLeft: { configurable: true, writable: true, value: 0 },
    })
    const scrollTo = vi.fn()
    Object.defineProperty(rail, 'scrollTo', { configurable: true, value: scrollTo })
    fireEvent.scroll(rail)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '查看后续推荐' }).hasAttribute('disabled')).toBe(false)
    })
    const controls = screen.getByLabelText('推荐活动翻页')
    const [previous, next] = within(controls).getAllByRole('button', { hidden: true })
    expect(previous.hasAttribute('disabled')).toBe(true)
    expect(previous.getAttribute('aria-hidden')).toBe('true')

    fireEvent.click(next)
    expect(scrollTo).toHaveBeenCalledWith({ behavior: 'smooth', left: 560 })

    Object.defineProperty(rail, 'scrollLeft', { configurable: true, value: 560 })
    fireEvent.scroll(rail)

    await waitFor(() => {
      expect(next.hasAttribute('disabled')).toBe(true)
    })
    expect(previous.hasAttribute('disabled')).toBe(false)
    expect(next.getAttribute('aria-hidden')).toBe('true')
  })
})
