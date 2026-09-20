// @vitest-environment jsdom

import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes, useNavigate } from 'react-router-dom'
import { getExploreActivity, listRelatedGroups, setActivityFavorite } from '@/api/explore'
import { getTopicCollaborators } from '@/api/management'
import { ToastProvider } from '@/components/Toast'
import { useAuthStore } from '@/store/authStore'
import TopicDetail from './TopicDetail'
import { attachPublicUpload, uploadTopicCover } from '@/api/publish'
import {
  activityDetailFixture,
  discussionGroup,
  officialSignupGroup,
  viewerFixture,
} from './detailTestFixtures'

vi.mock('@/api/explore', () => ({
  getExploreActivity: vi.fn(),
  listRelatedGroups: vi.fn(),
  setActivityFavorite: vi.fn(),
}))
vi.mock('@/api/management', () => ({
  getTopicCollaborators: vi.fn(),
  inviteTopicCollaborator: vi.fn(),
  revokeTopicCollaborator: vi.fn(),
}))
vi.mock('@/api/publish', () => ({ attachPublicUpload: vi.fn(), uploadTopicCover: vi.fn() }))

function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise
    reject = rejectPromise
  })
  return { promise, resolve, reject }
}

function RouteChange() {
  const navigate = useNavigate()
  return <button type="button" onClick={() => navigate('/topics/activity-2')}>打开另一个活动</button>
}

function renderTopic(initialEntry = '/topics/activity-1') {
  return render(
    <MemoryRouter initialEntries={[initialEntry]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <ToastProvider>
        <RouteChange />
        <Routes><Route path="/topics/:id" element={<TopicDetail />} /></Routes>
      </ToastProvider>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.resetAllMocks()
  useAuthStore.setState({ token: null, user: null, isAuthenticated: false })
  vi.mocked(getExploreActivity).mockResolvedValue(activityDetailFixture)
  vi.mocked(listRelatedGroups).mockImplementation(async (_topicId, params = {}) => {
    const list = activityDetailFixture.related_groups.filter((group) => !params.purpose || group.purpose === params.purpose)
    return { list, total: list.length, page: 1, page_size: 8, pages: list.length ? 1 : 0 }
  })
  vi.mocked(setActivityFavorite).mockResolvedValue({
    topic_id: activityDetailFixture.id,
    favorite: true,
    followed: true,
    follower_count: activityDetailFixture.follower_count + 1,
  })
  vi.mocked(getTopicCollaborators).mockResolvedValue({
    list: [], total: 0, page: 1, page_size: 20, pages: 0,
  })
  vi.mocked(uploadTopicCover).mockResolvedValue('replacement-topic-cover')
  vi.mocked(attachPublicUpload).mockResolvedValue({ upload_id: 'replacement-topic-cover', purpose: 'topic_cover', status: 'attached', target_id: activityDetailFixture.id })
  Object.defineProperty(navigator, 'share', { configurable: true, value: vi.fn().mockResolvedValue(undefined) })
  Object.defineProperty(navigator, 'clipboard', { configurable: true, value: undefined })
})

afterEach(() => cleanup())

describe('TopicDetail activity experience', () => {
  it('lets an activity manager upload a replacement cover', async () => {
    useAuthStore.setState({ token: 'token', user: viewerFixture, isAuthenticated: true })
    vi.mocked(getExploreActivity).mockResolvedValue({ ...activityDetailFixture, can_manage_collaborators: true })
    renderTopic()
    fireEvent.click(await screen.findByRole('button', { name: '编辑活动' }))

    const file = new File(['cover'], 'activity.webp', { type: 'image/webp' })
    fireEvent.change(screen.getByLabelText('更换活动封面'), { target: { files: [file] } })

    await waitFor(() => expect(uploadTopicCover).toHaveBeenCalledWith(file))
    expect(attachPublicUpload).toHaveBeenCalledWith('replacement-topic-cover', activityDetailFixture.id)
  })

  it.each([
    ['open_team', '寻找队友', true],
    ['official_signup', '进入官方报名', false],
    ['information_only', '查看相关讨论', false],
  ] as const)('uses the backend %s participation mode for one clear primary path', async (mode, actionName, hasPublish) => {
    vi.mocked(getExploreActivity).mockResolvedValue({
      ...activityDetailFixture,
      participation_mode: mode,
      related_groups: mode === 'official_signup'
        ? [officialSignupGroup]
        : mode === 'information_only'
          ? [discussionGroup]
          : activityDetailFixture.related_groups,
    })
    renderTopic()

    await screen.findByRole('heading', { level: 1, name: activityDetailFixture.title })
    expect(screen.getByRole('link', { name: actionName })).toBeTruthy()
    const publish = screen.queryByRole('link', { name: '发布组队' })
    expect(Boolean(publish)).toBe(hasPublish)
    if (publish) expect(publish.getAttribute('href')).toBe('/publish?kind=topic_team&topic_id=activity-1')
  })

  it('renders the approved hierarchy, complete long content, bounded people, and the active purpose label', async () => {
    const longTail = '末尾核对段落：请完整阅读后再报名。'
    const people = Array.from({ length: 10 }, (_, index) => ({
      id: `person-${index}`,
      nickname: `参与者${index}`,
      avatar: null,
      major: null,
      grade: null,
    }))
    vi.mocked(getExploreActivity).mockResolvedValue({
      ...activityDetailFixture,
      content: `${activityDetailFixture.content}\n\n${'详细说明。'.repeat(80)}${longTail}`,
      participant_preview: people,
    })
    renderTopic()

    const heading = await screen.findByRole('heading', { level: 1, name: activityDetailFixture.title })
    expect(screen.getByText(activityDetailFixture.organizer)).toBeTruthy()
    expect(screen.getByText('认证组织')).toBeTruthy()
    expect(screen.getByText(activityDetailFixture.location_name!)).toBeTruthy()
    expect(screen.getByText('40 人')).toBeTruthy()
    expect(screen.getByText(longTail, { exact: false })).toBeTruthy()
    expect(screen.getAllByRole('listitem', { name: /参与者/ })).toHaveLength(8)
    expect(screen.getByText('招募队友')).toBeTruthy()
    expect(heading.compareDocumentPosition(screen.getByRole('heading', { name: '活动详情' })) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('shows every active activity worker and gives managers an in-page authorization entry', async () => {
    const manager = {
      ...viewerFixture,
      id: 'manager-1',
      identity: {
        campus_verified: true,
        platform_role: null,
        organization_roles: [],
        topic_roles: [{ topic_id: activityDetailFixture.id, topic_title: activityDetailFixture.title, role: 'manager' as const }],
        post_roles: [],
      },
    }
    useAuthStore.setState({ token: 'token', user: manager, isAuthenticated: true })
    vi.mocked(getExploreActivity).mockResolvedValue({
      ...activityDetailFixture,
      can_manage_collaborators: true,
      responsible_people: [
        { user_id: 'manager-1', nickname: '周宁', role: 'manager', badge: '活动负责人' },
        { user_id: 'editor-2', nickname: '王老师', role: 'editor', badge: '活动组织者' },
        { user_id: 'helper-3', nickname: '林同学', role: 'coordinator', badge: '活动协作成员' },
      ],
    })
    renderTopic()

    const staff = await screen.findByRole('region', { name: '活动工作人员与权限' })
    expect(within(staff).getByText('周宁')).toBeTruthy()
    expect(within(staff).getByText('王老师')).toBeTruthy()
    expect(within(staff).getByText('林同学')).toBeTruthy()
    fireEvent.click(within(staff).getByRole('button', { name: '管理活动人员' }))
    expect(await screen.findByRole('heading', { name: '活动协作者' })).toBeTruthy()
    expect(screen.queryByLabelText('活动 ID')).toBeNull()
  })

  it('falls back from a broken cover without changing the media frame', async () => {
    renderTopic()
    const media = await screen.findByTestId('activity-detail-media')
    fireEvent.error(within(media).getByRole('img', { name: `${activityDetailFixture.title}封面` }))
    expect(within(media).getByRole('img', { name: '活动封面占位图' })).toBeTruthy()
    expect(media.classList.contains('aspect-[16/9]')).toBe(true)
  })

  it('shows the complete activity date range when an end time is provided', async () => {
    vi.mocked(getExploreActivity).mockResolvedValue({
      ...activityDetailFixture,
      activity_end_at: '2026-10-03T17:30:00+08:00',
    })
    renderTopic()
    const facts = await screen.findByRole('region', { name: '活动关键信息' })
    expect(within(facts).getByText(/至/).textContent).toContain('17:30')
  })

  it('keeps an empty related-groups section useful for the active participation mode', async () => {
    vi.mocked(getExploreActivity).mockResolvedValue({ ...activityDetailFixture, related_groups: [] })
    vi.mocked(listRelatedGroups).mockResolvedValue({ list: [], total: 0, page: 1, page_size: 8, pages: 0 })
    renderTopic()
    expect(await screen.findByText('还没有相关组队，成为第一个发起人。')).toBeTruthy()
    expect(screen.getByRole('link', { name: '发布组队' }).getAttribute('href')).toBe('/publish?kind=topic_team&topic_id=activity-1')
  })

  it('keeps every related-post category reachable instead of hiding recruitment posts', async () => {
    vi.mocked(getExploreActivity).mockResolvedValue({
      ...activityDetailFixture,
      participation_mode: 'official_signup',
      related_groups: activityDetailFixture.related_groups,
    })
    renderTopic()

    expect(await screen.findByRole('heading', { name: '人工智能挑战赛官方报名' })).toBeTruthy()
    fireEvent.click(screen.getByRole('tab', { name: '组队招募' }))
    expect(await screen.findByRole('heading', { name: '寻找前端同学一起参加机器人挑战赛' })).toBeTruthy()
    expect(listRelatedGroups).toHaveBeenCalledWith(activityDetailFixture.id, expect.objectContaining({ purpose: 'team_recruitment' }))

    fireEvent.click(screen.getByRole('tab', { name: '相关讨论' }))
    expect(await screen.findByRole('heading', { name: '挑战赛经验交流' })).toBeTruthy()
  })

  it('offers keyboard actions in a labelled sticky bar and updates favorite/share state', async () => {
    renderTopic()
    const actions = await screen.findByRole('region', { name: '活动操作' })
    const favorite = within(actions).getByRole('button', { name: '收藏活动' })
    fireEvent.click(favorite)
    await waitFor(() => expect(within(actions).getByRole('button', { name: '取消收藏活动' })).toBeTruthy())
    fireEvent.click(within(actions).getByRole('button', { name: '分享活动' }))
    expect(navigator.share).toHaveBeenCalled()
    expect(actions.getAttribute('data-mobile-safe-area')).toBe('true')
    expect(screen.getByTestId('activity-detail-page').className).toContain('pb-[calc(')
  })

  it('reports a share failure when the browser exposes no sharing API', async () => {
    Object.defineProperty(navigator, 'share', { configurable: true, value: undefined })
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: undefined })
    renderTopic()

    const actions = await screen.findByRole('region', { name: '活动操作' })
    fireEvent.click(within(actions).getByRole('button', { name: '分享活动' }))

    expect(await screen.findByText('暂时无法分享，请稍后重试')).toBeTruthy()
    expect(screen.queryByText('分享内容已准备好')).toBeNull()
  })

  it('shows an in-page failure with retry', async () => {
    vi.mocked(getExploreActivity)
      .mockRejectedValueOnce(new Error('offline'))
      .mockResolvedValueOnce(activityDetailFixture)
    renderTopic()
    expect((await screen.findByRole('alert')).textContent).toContain('活动加载失败')
    fireEvent.click(screen.getByRole('button', { name: '重新加载' }))
    expect(await screen.findByRole('heading', { level: 1, name: activityDetailFixture.title })).toBeTruthy()
  })

  it('ignores a stale activity response after the route id changes', async () => {
    const stale = deferred<typeof activityDetailFixture>()
    const current = { ...activityDetailFixture, id: 'activity-2', title: '当前活动详情' }
    vi.mocked(getExploreActivity).mockReturnValueOnce(stale.promise).mockResolvedValueOnce(current)
    renderTopic()
    fireEvent.click(screen.getByRole('button', { name: '打开另一个活动' }))
    expect(await screen.findByRole('heading', { name: '当前活动详情' })).toBeTruthy()
    await act(async () => { stale.resolve(activityDetailFixture); await stale.promise })
    expect(screen.queryByText(activityDetailFixture.title)).toBeNull()
  })
})
