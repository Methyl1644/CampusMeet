// @vitest-environment jsdom

import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, useLocation, useNavigate } from 'react-router-dom'
import {
  listExploreActivities,
  listExploreGroups,
  setActivityFavorite,
  setGroupFavorite,
} from '@/api/explore'
import { ToastProvider } from '@/components/Toast'
import { activityFixture, groupFixture } from '@/components/explore/exploreTestFixtures'
import Discover from './Discover'

vi.mock('@/api/explore', () => ({
  listExploreActivities: vi.fn(),
  listExploreGroups: vi.fn(),
  setActivityFavorite: vi.fn(),
  setGroupFavorite: vi.fn(),
}))

const activityPage = {
  list: [activityFixture],
  total: 41,
  page: 1,
  page_size: 12,
  pages: 4,
}
const groupPage = {
  list: [groupFixture],
  total: 1,
  page: 1,
  page_size: 12,
  pages: 1,
}

function LocationProbe() {
  const location = useLocation()
  const navigate = useNavigate()
  return (
    <>
      <output aria-label="当前地址">{location.pathname}{location.search}</output>
      <button type="button" onClick={() => navigate(-1)}>返回上一地址</button>
    </>
  )
}

function renderDiscover(initialEntry = '/discover', previousEntry?: string) {
  return render(
    <MemoryRouter
      initialEntries={previousEntry ? [previousEntry, initialEntry] : [initialEntry]}
      initialIndex={previousEntry ? 1 : 0}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <ToastProvider>
        <Discover />
        <LocationProbe />
      </ToastProvider>
    </MemoryRouter>,
  )
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

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(listExploreActivities).mockResolvedValue(activityPage)
  vi.mocked(listExploreGroups).mockResolvedValue(groupPage)
  vi.mocked(setActivityFavorite).mockResolvedValue({
    topic_id: activityFixture.id,
    favorite: true,
    followed: true,
    follower_count: activityFixture.follower_count + 1,
  })
  vi.mocked(setGroupFavorite).mockResolvedValue({ post_id: groupFixture.id, bookmark: true })
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('Discover Explore experience', () => {
  it('renders exactly two keyboard tabs, a dynamic heading, and search below the heading', async () => {
    renderDiscover()

    const tablist = screen.getByRole('tablist', { name: '探索分类' })
    const tabs = within(tablist).getAllByRole('tab')
    expect(tabs.map((tab) => tab.textContent)).toEqual(['活动', '组队'])
    expect(tabs[0].getAttribute('aria-selected')).toBe('true')
    const heading = screen.getByRole('heading', { level: 1, name: '发现值得认真准备的校园活动' })
    expect(heading.classList.contains('font-bold')).toBe(true)
    const search = screen.getByRole('searchbox', { name: '搜索活动' })
    expect(heading.compareDocumentPosition(search) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()

    fireEvent.keyDown(tabs[0], { key: 'ArrowRight' })
    await waitFor(() => expect(screen.getByRole('heading', { level: 1 }).textContent).toBe('找到此刻正缺你的队伍'))
    expect(document.activeElement).toBe(tabs[1])
    expect(screen.getByRole('searchbox', { name: '搜索组队' })).toBeTruthy()
  })

  it('restores independent URL-backed search and filters when switching views', async () => {
    renderDiscover('/discover?activity_q=%E6%9C%BA%E5%99%A8%E4%BA%BA&activity_campus=%E4%BB%99%E6%9E%97%E6%A0%A1%E5%8C%BA&group_q=%E9%9F%B3%E4%B9%90&group_status=recruiting')

    expect(screen.getByRole('searchbox', { name: '搜索活动' }).getAttribute('value')).toBe('机器人')
    expect((screen.getByLabelText('活动校区') as HTMLSelectElement).value).toBe('仙林校区')

    fireEvent.click(screen.getByRole('tab', { name: '组队' }))
    expect(screen.getByRole('searchbox', { name: '搜索组队' }).getAttribute('value')).toBe('音乐')
    expect((screen.getByLabelText('组队状态') as HTMLSelectElement).value).toBe('recruiting')

    fireEvent.change(screen.getByRole('searchbox', { name: '搜索组队' }), { target: { value: '摄影' } })
    fireEvent.click(screen.getByRole('tab', { name: '活动' }))
    expect(screen.getByRole('searchbox', { name: '搜索活动' }).getAttribute('value')).toBe('机器人')
    expect(screen.getByLabelText('当前地址').textContent).toContain('group_q=%E6%91%84%E5%BD%B1')
  })

  it('uses compact filters, an explicitly ordered category rail, and only effective latest ordering', async () => {
    renderDiscover()
    await screen.findByText(activityFixture.title)

    expect(screen.getByLabelText('活动日期')).toBeTruthy()
    expect(screen.getByLabelText('活动状态')).toBeTruthy()
    expect(screen.getByLabelText('活动类型')).toBeTruthy()
    expect(screen.getByLabelText('活动校区')).toBeTruthy()
    const categories = within(screen.getByRole('region', { name: '兴趣分类' })).getAllByRole('button')
    expect(categories.slice(0, 5).map((button) => button.textContent)).toEqual([
      '全部', '人工智能', '创新创业', '程序设计', '机器人',
    ])
    expect(categories.slice(7, 9).map((button) => button.textContent)).toEqual(['羽毛球', '摄影'])
    expect(screen.queryByText('热门排序')).toBeNull()
    expect(screen.queryByText('截止优先')).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: '人工智能' }))
    await waitFor(() => expect(listExploreActivities).toHaveBeenLastCalledWith(
      expect.objectContaining({ tagIds: ['activity_ai'], page: 1, pageSize: 12 }),
      expect.any(AbortSignal),
    ))

    fireEvent.click(screen.getByRole('button', { name: '摄影' }))
    await waitFor(() => expect(listExploreActivities).toHaveBeenLastCalledWith(
      expect.objectContaining({ tagIds: ['activity_ai', 'activity_photography'] }),
      expect.any(AbortSignal),
    ))
  })

  it('opens a labelled mobile filter dialog, traps Escape, and returns focus to its trigger', async () => {
    renderDiscover()
    const trigger = screen.getByRole('button', { name: '打开筛选' })
    trigger.focus()
    fireEvent.click(trigger)

    const dialog = screen.getByRole('dialog', { name: '筛选活动' })
    const closeButton = within(dialog).getByRole('button', { name: '关闭筛选' })
    const applyButton = within(dialog).getByRole('button', { name: '查看结果' })
    expect(document.activeElement).toBe(closeButton)
    fireEvent.keyDown(dialog, { key: 'Tab', shiftKey: true })
    expect(document.activeElement).toBe(applyButton)
    fireEvent.keyDown(dialog, { key: 'Tab' })
    expect(document.activeElement).toBe(closeButton)
    fireEvent.keyDown(dialog, { key: 'Escape' })

    expect(screen.queryByRole('dialog', { name: '筛选活动' })).toBeNull()
    await waitFor(() => expect(document.activeElement).toBe(trigger))
  })

  it('renders stable loading, empty, error/retry, and paginated result states', async () => {
    const pending = deferred<typeof activityPage>()
    vi.mocked(listExploreActivities).mockReturnValueOnce(pending.promise)
    const first = renderDiscover()
    expect(screen.getByRole('status', { name: '正在加载活动' })).toBeTruthy()
    pending.resolve({ ...activityPage, list: [], total: 0, pages: 0 })
    expect(await screen.findByText('没有找到符合条件的活动')).toBeTruthy()
    first.unmount()

    vi.mocked(listExploreActivities)
      .mockRejectedValueOnce(new Error('offline'))
      .mockResolvedValueOnce(activityPage)
    renderDiscover()
    expect((await screen.findByRole('alert')).textContent).toContain('活动加载失败')
    fireEvent.click(screen.getByRole('button', { name: '重新加载' }))
    expect(await screen.findByText(activityFixture.title)).toBeTruthy()
    expect(screen.getByText('第 1 / 4 页')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '下一页' }))
    await waitFor(() => expect(listExploreActivities).toHaveBeenLastCalledWith(
      expect.objectContaining({ page: 2, pageSize: 12 }),
      expect.any(AbortSignal),
    ))
  })

  it('normalizes an out-of-range shared URL with history replacement and preserves inactive state', async () => {
    vi.mocked(listExploreGroups)
      .mockResolvedValueOnce({ ...groupPage, list: [], total: 13, page: 7, pages: 2 })
      .mockResolvedValueOnce({ ...groupPage, page: 2, pages: 2 })

    renderDiscover(
      '/discover?view=group&group_page=7&activity_page=4&activity_q=robot',
      '/home',
    )

    expect(await screen.findByText(groupFixture.title)).toBeTruthy()
    expect(vi.mocked(listExploreGroups).mock.calls.map(([params]) => params?.page)).toEqual([7, 2])
    const correctedUrl = screen.getByLabelText('当前地址').textContent ?? ''
    expect(correctedUrl).toContain('group_page=2')
    expect(correctedUrl).toContain('activity_page=4')
    expect(correctedUrl).toContain('activity_q=robot')

    fireEvent.click(screen.getByRole('button', { name: '返回上一地址' }))
    await waitFor(() => expect(screen.getByLabelText('当前地址').textContent).toBe('/home'))
  })

  it('does not let an older success replace a newer activity result', async () => {
    const staleRequest = deferred<typeof activityPage>()
    const currentActivity = { ...activityFixture, id: 'activity-current', title: '当前搜索结果' }
    vi.mocked(listExploreActivities)
      .mockReturnValueOnce(staleRequest.promise)
      .mockResolvedValueOnce({ ...activityPage, list: [currentActivity] })

    renderDiscover()
    await waitFor(() => expect(listExploreActivities).toHaveBeenCalledTimes(1))
    fireEvent.change(screen.getByRole('searchbox', { name: '搜索活动' }), { target: { value: '当前' } })
    expect(await screen.findByText(currentActivity.title)).toBeTruthy()

    await act(async () => {
      staleRequest.resolve(activityPage)
      await staleRequest.promise
    })

    expect(screen.getByText(currentActivity.title)).toBeTruthy()
    expect(screen.queryByText(activityFixture.title)).toBeNull()
  })

  it('does not let an older error replace a newer activity result', async () => {
    const staleRequest = deferred<typeof activityPage>()
    const currentActivity = { ...activityFixture, id: 'activity-current', title: '错误之后仍保留的结果' }
    vi.mocked(listExploreActivities)
      .mockReturnValueOnce(staleRequest.promise)
      .mockResolvedValueOnce({ ...activityPage, list: [currentActivity] })

    renderDiscover()
    await waitFor(() => expect(listExploreActivities).toHaveBeenCalledTimes(1))
    fireEvent.change(screen.getByRole('searchbox', { name: '搜索活动' }), { target: { value: '保留' } })
    expect(await screen.findByText(currentActivity.title)).toBeTruthy()

    await act(async () => {
      staleRequest.reject(new Error('stale failure'))
      try {
        await staleRequest.promise
      } catch {
        // The component owns the expected rejection; awaiting it flushes the stale catch path.
      }
    })

    expect(screen.queryByRole('alert')).toBeNull()
    expect(screen.getByText(currentActivity.title)).toBeTruthy()
  })

  it('matches the loading placeholder height to group card geometry', () => {
    vi.mocked(listExploreGroups).mockReturnValueOnce(deferred<typeof groupPage>().promise)
    renderDiscover('/discover?view=group')

    const skeleton = screen.getByRole('status', { name: '正在加载组队' })
    expect(skeleton.firstElementChild?.nextElementSibling?.classList.contains('h-[444px]')).toBe(true)
  })

  it('optimistically favorites an activity and rolls back with actionable feedback on failure', async () => {
    const mutation = deferred<never>()
    vi.mocked(setActivityFavorite).mockReturnValueOnce(mutation.promise)
    renderDiscover()
    await screen.findByText(activityFixture.title)

    const addButton = screen.getByRole('button', { name: `收藏${activityFixture.title}` })
    fireEvent.click(addButton)
    expect(screen.getByRole('button', { name: `取消收藏${activityFixture.title}` })).toBeTruthy()

    mutation.reject(new Error('offline'))
    await waitFor(() => expect(screen.getByRole('button', { name: `收藏${activityFixture.title}` })).toBeTruthy())
    expect(screen.getByRole('alert').textContent).toContain('收藏失败，已恢复原状态')
  })

  it('does not overwrite fresher activity metadata when a favorite rollback arrives late', async () => {
    const mutation = deferred<never>()
    const refreshedActivity = { ...activityFixture, title: '机器人挑战赛最新安排', follower_count: 160 }
    vi.mocked(setActivityFavorite).mockReturnValueOnce(mutation.promise)
    renderDiscover()
    await screen.findByText(activityFixture.title)

    fireEvent.click(screen.getByRole('button', { name: `收藏${activityFixture.title}` }))
    vi.mocked(listExploreActivities).mockResolvedValueOnce({ ...activityPage, list: [refreshedActivity] })
    fireEvent.change(screen.getByRole('searchbox', { name: '搜索活动' }), { target: { value: '机器人' } })
    expect(await screen.findByText(refreshedActivity.title)).toBeTruthy()

    mutation.reject(new Error('offline'))
    await waitFor(() => expect(screen.getByRole('button', { name: `收藏${refreshedActivity.title}` })).toBeTruthy())
    expect(screen.getByText(refreshedActivity.title)).toBeTruthy()
  })

  it('optimistically favorites a group and rolls back when the bookmark request fails', async () => {
    const mutation = deferred<never>()
    vi.mocked(setGroupFavorite).mockReturnValueOnce(mutation.promise)
    renderDiscover('/discover?view=group')
    await screen.findByText(groupFixture.title)

    fireEvent.click(screen.getByRole('button', { name: `收藏${groupFixture.title}` }))
    expect(screen.getByRole('button', { name: `取消收藏${groupFixture.title}` })).toBeTruthy()

    mutation.reject(new Error('offline'))
    await waitFor(() => expect(screen.getByRole('button', { name: `收藏${groupFixture.title}` })).toBeTruthy())
    expect(screen.getByRole('alert').textContent).toContain('收藏失败，已恢复原状态')
  })
})
