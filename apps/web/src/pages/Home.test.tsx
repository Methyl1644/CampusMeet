// @vitest-environment jsdom

import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import type { HomeFeed, RecommendedHomeTopic } from '@shared/types'
import { getHomeFeed } from '@/api/home'
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

afterEach(cleanup)

describe('Home', () => {
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
    expect(screen.getByText('小组有新任务时，会在这里按日期出现。')).toBeTruthy()
    expect(screen.getByRole('link', { name: '探索组队' }).getAttribute('href')).toBe(
      '/discover?view=groups',
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
    expect(within(loading).getByTestId('home-skeleton-sidebar').className).toContain('min-h')
    expect(within(loading).getAllByTestId('home-skeleton-event')[0].className).toContain('w-')
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
