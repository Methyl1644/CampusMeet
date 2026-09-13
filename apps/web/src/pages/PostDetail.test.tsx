// @vitest-environment jsdom

import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes, useNavigate } from 'react-router-dom'
import { createApplication } from '@/api/applications'
import { getExploreGroup, joinExploreGroup, setGroupFavorite } from '@/api/explore'
import { getMyTeams, type MyTeamSummary } from '@/api/teams'
import { ToastProvider } from '@/components/Toast'
import PostDetail from './PostDetail'
import { groupDetailFixture } from './detailTestFixtures'

vi.mock('@/api/applications', () => ({ createApplication: vi.fn() }))
vi.mock('@/api/explore', () => ({
  getExploreGroup: vi.fn(),
  joinExploreGroup: vi.fn(),
  setGroupFavorite: vi.fn(),
}))
vi.mock('@/api/teams', () => ({ getMyTeams: vi.fn() }))

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((resolvePromise) => { resolve = resolvePromise })
  return { promise, resolve }
}

const myTeamSummaryFixture: MyTeamSummary = {
  id: 'team-1',
  post_id: groupDetailFixture.id,
  activity_name: groupDetailFixture.activity_name,
  my_role: '队长',
  created_at: '2026-09-13T08:00:00+08:00',
}

function teamPage(
  list: MyTeamSummary[],
  { page = 1, pageSize = 100, pages = 1, total = list.length } = {},
) {
  return { list, total, page, page_size: pageSize, pages }
}

function RouteChange() {
  const navigate = useNavigate()
  return (
    <>
      <button type="button" onClick={() => navigate('/posts/group-2')}>打开另一个组队</button>
      <button type="button" onClick={() => navigate('/posts/group-1')}>返回原组队</button>
    </>
  )
}

function renderPost() {
  return render(
    <MemoryRouter initialEntries={['/posts/group-1']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <ToastProvider>
        <RouteChange />
        <Routes><Route path="/posts/:id" element={<PostDetail />} /></Routes>
      </ToastProvider>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(getExploreGroup).mockResolvedValue(groupDetailFixture)
  vi.mocked(setGroupFavorite).mockResolvedValue({ post_id: groupDetailFixture.id, bookmark: true })
  vi.mocked(getMyTeams).mockResolvedValue(teamPage([myTeamSummaryFixture]))
  vi.mocked(joinExploreGroup).mockResolvedValue({
    ...groupDetailFixture,
    join_state: 'joined',
    team_id: 'team-1',
    member_id: 'member-1',
  })
  vi.mocked(createApplication).mockResolvedValue({
    id: 'application-1',
    post_id: groupDetailFixture.id,
    applicant: { id: 'viewer-1', nickname: '周宁', auth_status: 'campus_verified' },
    role_wanted: '前端开发', experience: '有项目经验', available_time: '', reason: '希望一起参赛',
    status: 'pending', created_at: '2026-09-13T08:00:00+08:00',
  })
  Object.defineProperty(navigator, 'share', { configurable: true, value: vi.fn().mockResolvedValue(undefined) })
})

afterEach(() => cleanup())

describe('PostDetail group experience', () => {
  it.each([
    ['owner', '管理组队'],
    ['pending', '申请审核中'],
    ['rejected', '申请未通过'],
    ['closed', '暂不可加入'],
  ] as const)('renders the backend %s join state without recomputing eligibility', async (joinState, actionName) => {
    vi.mocked(getExploreGroup).mockResolvedValue({ ...groupDetailFixture, join_state: joinState })
    renderPost()
    const actions = await screen.findByRole('region', { name: '组队操作' })
    expect(within(actions).getByText(actionName)).toBeTruthy()
    expect(within(actions).queryByRole('button', { name: '申请加入' })).toBeNull()
    expect(within(actions).queryByRole('button', { name: '直接加入' })).toBeNull()
  })

  it('finds a previously joined post on a later bounded team page', async () => {
    vi.mocked(getExploreGroup).mockResolvedValue({ ...groupDetailFixture, join_state: 'joined' })
    vi.mocked(getMyTeams)
      .mockResolvedValueOnce(teamPage(
        [{ ...myTeamSummaryFixture, id: 'unrelated-team', post_id: 'another-post' }],
        { page: 1, pages: 2, total: 101 },
      ))
      .mockResolvedValueOnce(teamPage(
        [{ ...myTeamSummaryFixture, id: 'matching-team', post_id: groupDetailFixture.id }],
        { page: 2, pages: 2, total: 101 },
      ))
    renderPost()

    const teamLink = await screen.findByRole('link', { name: '进入团队' })
    expect(teamLink.getAttribute('href')).toBe('/teams/matching-team')
    expect(getMyTeams).toHaveBeenNthCalledWith(1, { page: 1, page_size: 100 })
    expect(getMyTeams).toHaveBeenNthCalledWith(2, { page: 2, page_size: 100 })
  })

  it('offers a retry only after a previously joined team is genuinely unresolved', async () => {
    vi.mocked(getExploreGroup).mockResolvedValue({ ...groupDetailFixture, join_state: 'joined' })
    vi.mocked(getMyTeams).mockResolvedValue(teamPage([]))
    renderPost()

    const retry = await screen.findByRole('button', { name: '重新查找团队' })
    expect(getMyTeams).toHaveBeenCalledTimes(1)
    fireEvent.click(retry)
    await waitFor(() => expect(getMyTeams).toHaveBeenCalledTimes(2))
  })

  it('opens the existing application modal only for an available application group', async () => {
    renderPost()
    const button = await screen.findByRole('button', { name: '申请加入' })
    fireEvent.click(button)
    expect(screen.getByRole('dialog', { name: '申请加入' })).toBeTruthy()
  })

  it('submits an application with a stable unrestricted role when no roles are listed', async () => {
    vi.mocked(getExploreGroup).mockResolvedValue({ ...groupDetailFixture, needed_roles: [] })
    renderPost()
    fireEvent.click(await screen.findByRole('button', { name: '申请加入' }))

    expect(screen.getByRole('button', { name: '不限角色' }).getAttribute('aria-pressed')).toBe('true')
    fireEvent.change(screen.getByLabelText(/相关经验/), { target: { value: '参加过校内项目' } })
    fireEvent.change(screen.getByLabelText(/可投入时间/), { target: { value: '每周四小时' } })
    fireEvent.change(screen.getByLabelText(/加入原因/), { target: { value: '希望共同完成作品' } })
    fireEvent.click(screen.getByRole('button', { name: '提交申请' }))

    await waitFor(() => expect(createApplication).toHaveBeenCalledWith({
      post_id: groupDetailFixture.id,
      role_wanted: '不限角色',
      experience: '参加过校内项目',
      available_time: '每周四小时',
      reason: '希望共同完成作品',
      questions: undefined,
    }))
    expect(screen.queryByRole('dialog', { name: '申请加入' })).toBeNull()
    expect(screen.getByText('申请审核中')).toBeTruthy()
  })

  it('directly joins only an available direct group and links to the returned team', async () => {
    vi.mocked(getExploreGroup).mockResolvedValue({ ...groupDetailFixture, join_mode: 'direct' })
    renderPost()
    fireEvent.click(await screen.findByRole('button', { name: '直接加入' }))
    const teamLink = await screen.findByRole('link', { name: '进入团队' })
    expect(teamLink.getAttribute('href')).toBe('/teams/team-1')
  })

  it('keeps available none groups informational and never exposes a join command', async () => {
    vi.mocked(getExploreGroup).mockResolvedValue({ ...groupDetailFixture, join_mode: 'none' })
    renderPost()
    const actions = await screen.findByRole('region', { name: '组队操作' })
    expect(within(actions).getByText('仅供交流')).toBeTruthy()
    expect(within(actions).queryByRole('button', { name: /加入/ })).toBeNull()
  })

  it('shows full separately from a generally closed group after the backend closes joining', async () => {
    vi.mocked(getExploreGroup).mockResolvedValue({ ...groupDetailFixture, join_state: 'closed', status: 'full' })
    renderPost()
    expect(await screen.findByText('人数已满')).toBeTruthy()
  })

  it('renders purpose, linked activity, complete description, bounded members, and resilient cover', async () => {
    const members = Array.from({ length: 10 }, (_, index) => ({
      id: `member-${index}`, nickname: `成员${index}`, avatar: null, major: null, grade: null,
    }))
    const tail = '最后一段不会被折叠。'
    vi.mocked(getExploreGroup).mockResolvedValue({
      ...groupDetailFixture,
      cover_url: '/broken.jpg',
      description: `${'详细组队说明。'.repeat(70)}${tail}`,
      member_preview: members,
    })
    renderPost()
    expect(await screen.findByText('招募队友')).toBeTruthy()
    expect(screen.getByRole('link', { name: /关联活动/ }).getAttribute('href')).toBe('/topics/activity-1')
    expect(screen.getByText(tail, { exact: false })).toBeTruthy()
    expect(screen.getAllByRole('listitem', { name: /成员/ })).toHaveLength(8)
    const media = screen.getByTestId('group-detail-media')
    fireEvent.error(within(media).getByRole('img', { name: `${groupDetailFixture.title}封面` }))
    expect(within(media).getByRole('img', { name: '组队封面占位图' })).toBeTruthy()
  })

  it('provides favorite/share controls and matching page padding for the safe-area bar', async () => {
    renderPost()
    const actions = await screen.findByRole('region', { name: '组队操作' })
    fireEvent.click(within(actions).getByRole('button', { name: '收藏组队' }))
    await waitFor(() => expect(within(actions).getByRole('button', { name: '取消收藏组队' })).toBeTruthy())
    fireEvent.click(within(actions).getByRole('button', { name: '分享组队' }))
    expect(navigator.share).toHaveBeenCalled()
    expect(actions.getAttribute('data-mobile-safe-area')).toBe('true')
    expect(screen.getByTestId('group-detail-page').className).toContain('pb-[calc(')
  })

  it('retries a failed detail request and ignores an older successful route response', async () => {
    vi.mocked(getExploreGroup).mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce(groupDetailFixture)
    renderPost()
    expect((await screen.findByRole('alert')).textContent).toContain('组队加载失败')
    fireEvent.click(screen.getByRole('button', { name: '重新加载' }))
    expect(await screen.findByRole('heading', { name: groupDetailFixture.title })).toBeTruthy()

    cleanup()
    const stale = deferred<typeof groupDetailFixture>()
    const current = { ...groupDetailFixture, id: 'group-2', title: '当前组队详情' }
    vi.mocked(getExploreGroup).mockReturnValueOnce(stale.promise).mockResolvedValueOnce(current)
    renderPost()
    fireEvent.click(screen.getByRole('button', { name: '打开另一个组队' }))
    expect(await screen.findByRole('heading', { name: current.title })).toBeTruthy()
    await act(async () => { stale.resolve(groupDetailFixture); await stale.promise })
    expect(screen.queryByText(groupDetailFixture.title)).toBeNull()
  })

  it('does not let a hung direct join own the next joinable post state or feedback', async () => {
    const joining = deferred<Awaited<ReturnType<typeof joinExploreGroup>>>()
    const directGroup = { ...groupDetailFixture, join_mode: 'direct' as const }
    const currentGroup = {
      ...groupDetailFixture,
      id: 'group-2',
      title: '导航后的组队',
      join_state: 'available' as const,
      join_mode: 'direct' as const,
    }
    vi.mocked(getExploreGroup).mockResolvedValueOnce(directGroup).mockResolvedValueOnce(currentGroup)
    vi.mocked(joinExploreGroup).mockReturnValueOnce(joining.promise)
    renderPost()

    fireEvent.click(await screen.findByRole('button', { name: '直接加入' }))
    fireEvent.click(screen.getByRole('button', { name: '打开另一个组队' }))
    expect(await screen.findByRole('heading', { name: currentGroup.title })).toBeTruthy()
    expect(screen.getByRole('button', { name: '直接加入' }).hasAttribute('disabled')).toBe(false)

    await act(async () => {
      joining.resolve({ ...directGroup, join_state: 'joined', team_id: 'old-team', member_id: 'old-member' })
      await joining.promise
    })

    expect(screen.getByRole('heading', { name: currentGroup.title })).toBeTruthy()
    expect(screen.getByRole('button', { name: '直接加入' }).hasAttribute('disabled')).toBe(false)
    expect(screen.queryByText('已加入组队')).toBeNull()
  })

  it('does not let an old A join commit or clear a fresh A join after A to B to A navigation', async () => {
    const oldJoin = deferred<Awaited<ReturnType<typeof joinExploreGroup>>>()
    const freshJoin = deferred<Awaited<ReturnType<typeof joinExploreGroup>>>()
    const firstA = { ...groupDetailFixture, join_mode: 'direct' as const }
    const groupB = { ...firstA, id: 'group-2', title: '中间组队' }
    const freshA = { ...firstA, title: '重新进入的原组队' }
    vi.mocked(getExploreGroup)
      .mockResolvedValueOnce(firstA)
      .mockResolvedValueOnce(groupB)
      .mockResolvedValueOnce(freshA)
    vi.mocked(joinExploreGroup).mockReturnValueOnce(oldJoin.promise).mockReturnValueOnce(freshJoin.promise)
    renderPost()

    fireEvent.click(await screen.findByRole('button', { name: '直接加入' }))
    fireEvent.click(screen.getByRole('button', { name: '打开另一个组队' }))
    expect(await screen.findByRole('heading', { name: groupB.title })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '返回原组队' }))
    expect(await screen.findByRole('heading', { name: freshA.title })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '直接加入' }))
    expect(screen.getByRole('button', { name: '加入中...' }).hasAttribute('disabled')).toBe(true)

    await act(async () => {
      oldJoin.resolve({ ...firstA, join_state: 'joined', team_id: 'old-team', member_id: 'old-member' })
      await oldJoin.promise
    })

    expect(screen.getByRole('heading', { name: freshA.title })).toBeTruthy()
    expect(screen.getByRole('button', { name: '加入中...' }).hasAttribute('disabled')).toBe(true)
    expect(screen.queryByRole('link', { name: '进入团队' })).toBeNull()
    expect(screen.queryByText('已加入组队')).toBeNull()

    await act(async () => {
      freshJoin.resolve({ ...freshA, join_state: 'joined', team_id: 'fresh-team', member_id: 'fresh-member' })
      await freshJoin.promise
    })
    expect((await screen.findByRole('link', { name: '进入团队' })).getAttribute('href')).toBe('/teams/fresh-team')
  })

  it('does not reuse an old A team lookup when fresh A is still loading', async () => {
    const oldLookup = deferred<Awaited<ReturnType<typeof getMyTeams>>>()
    const freshARequest = deferred<typeof groupDetailFixture>()
    const joinedA = { ...groupDetailFixture, join_state: 'joined' as const }
    const groupB = { ...groupDetailFixture, id: 'group-2', title: '中间组队' }
    const freshA = { ...joinedA, title: '重新加载的原组队' }
    vi.mocked(getExploreGroup)
      .mockResolvedValueOnce(joinedA)
      .mockResolvedValueOnce(groupB)
      .mockReturnValueOnce(freshARequest.promise)
    vi.mocked(getMyTeams)
      .mockReturnValueOnce(oldLookup.promise)
      .mockResolvedValueOnce(teamPage([{ ...myTeamSummaryFixture, id: 'fresh-team' }]))
    renderPost()

    expect(await screen.findByText('正在查找团队...')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '打开另一个组队' }))
    expect(await screen.findByRole('heading', { name: groupB.title })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '返回原组队' }))
    expect(await screen.findByRole('status', { name: '正在加载组队详情' })).toBeTruthy()

    await act(async () => {
      oldLookup.resolve(teamPage([{ ...myTeamSummaryFixture, id: 'old-team' }]))
      await oldLookup.promise
      freshARequest.resolve(freshA)
      await freshARequest.promise
    })

    const teamLink = await screen.findByRole('link', { name: '进入团队' })
    expect(teamLink.getAttribute('href')).toBe('/teams/fresh-team')
  })
})
