// @vitest-environment jsdom

import { StrictMode } from 'react'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { HomeFeed } from '@shared/types'
import { getHomeFeed } from '@/api/home'
import { HomeFeedProvider, useHomeFeed } from './HomeFeedContext'
import { createHomeFeedRequestGate } from './HomeFeedRequestGate'

vi.mock('@/api/home', () => ({
  getHomeFeed: vi.fn(),
}))

const feed: HomeFeed = {
  profile: {
    id: 'student-1',
    nickname: 'Lin',
    avatar: null,
    major: 'Software Engineering',
    grade: 'Junior',
  },
  deadline_reminder: null,
  recommended_topics: [],
  attending_topics: [],
  followed_topics: [],
  joined_groups: [],
  group_timeline: [],
  unread: {
    messages: 2,
    notifications: 1,
  },
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

function feedNamed(nickname: string): HomeFeed {
  return {
    ...feed,
    profile: { ...feed.profile, nickname },
  }
}

function Consumer({ name }: { name: string }) {
  const { feed: currentFeed, loading, error, reload } = useHomeFeed()

  return (
    <section aria-label={name}>
      <span>{currentFeed?.profile.nickname ?? 'no feed'}</span>
      <span>{loading ? 'loading' : 'idle'}</span>
      <span>{error instanceof Error ? error.message : 'no error'}</span>
      <button type="button" onClick={() => void reload()}>
        Reload {name}
      </button>
    </section>
  )
}

beforeEach(() => {
  vi.clearAllMocks()
})

afterEach(cleanup)

describe('HomeFeedRequestGate', () => {
  it('suppresses an observable late transition after disposal', async () => {
    const request = deferred<HomeFeed>()
    const gate = createHomeFeedRequestGate()
    const requestId = gate.begin()
    const committedFeeds: HomeFeed[] = []
    const completion = request.promise.then((nextFeed) => {
      gate.commit(requestId, () => committedFeeds.push(nextFeed))
    })

    gate.dispose()
    request.resolve(feed)
    await completion

    expect(committedFeeds).toEqual([])
  })
})

describe('HomeFeedProvider', () => {
  it('shares one mount request and the same resolved state with multiple consumers', async () => {
    const request = deferred<HomeFeed>()
    vi.mocked(getHomeFeed).mockReturnValue(request.promise)

    render(
      <StrictMode>
        <HomeFeedProvider>
          <Consumer name="first" />
          <Consumer name="second" />
        </HomeFeedProvider>
      </StrictMode>,
    )

    expect(getHomeFeed).toHaveBeenCalledOnce()
    expect(screen.getByLabelText('first').textContent).toContain('loading')
    expect(screen.getByLabelText('second').textContent).toContain('loading')

    await act(async () => request.resolve(feed))

    await waitFor(() => expect(screen.getByLabelText('first').textContent).toContain('Linidle'))
    expect(screen.getByLabelText('second').textContent).toContain('Linidle')
    expect(getHomeFeed).toHaveBeenCalledOnce()
  })

  it('retries after an error', async () => {
    const retry = deferred<HomeFeed>()
    vi.mocked(getHomeFeed)
      .mockRejectedValueOnce(new Error('Home unavailable'))
      .mockReturnValueOnce(retry.promise)

    render(
      <HomeFeedProvider>
        <Consumer name="feed" />
      </HomeFeedProvider>,
    )

    await screen.findByText('Home unavailable')
    fireEvent.click(screen.getByRole('button', { name: 'Reload feed' }))

    expect(getHomeFeed).toHaveBeenCalledTimes(2)
    expect(screen.getByLabelText('feed').textContent).toContain('loading')

    await act(async () => retry.resolve(feed))
    await waitFor(() => expect(screen.getByLabelText('feed').textContent).toContain('Linidle'))
    expect(screen.getByLabelText('feed').textContent).toContain('no error')
  })

  it('retains the last successful feed while a reload is pending', async () => {
    const reload = deferred<HomeFeed>()
    vi.mocked(getHomeFeed)
      .mockResolvedValueOnce(feed)
      .mockReturnValueOnce(reload.promise)

    render(
      <HomeFeedProvider>
        <Consumer name="feed" />
      </HomeFeedProvider>,
    )

    await screen.findByText('Lin')
    fireEvent.click(screen.getByRole('button', { name: 'Reload feed' }))

    expect(screen.getByLabelText('feed').textContent).toContain('Linloading')

    await act(async () => reload.resolve({
      ...feed,
      profile: { ...feed.profile, nickname: 'Mei' },
    }))
    await screen.findByText('Mei')
  })

  it('keeps the newer feed when an older reload resolves last', async () => {
    const olderReload = deferred<HomeFeed>()
    const newerReload = deferred<HomeFeed>()
    vi.mocked(getHomeFeed)
      .mockResolvedValueOnce(feed)
      .mockReturnValueOnce(olderReload.promise)
      .mockReturnValueOnce(newerReload.promise)

    render(
      <HomeFeedProvider>
        <Consumer name="feed" />
      </HomeFeedProvider>,
    )

    await screen.findByText('Lin')
    fireEvent.click(screen.getByRole('button', { name: 'Reload feed' }))
    fireEvent.click(screen.getByRole('button', { name: 'Reload feed' }))

    await act(async () => newerReload.resolve(feedNamed('Newest')))
    await screen.findByText('Newest')
    expect(screen.getByLabelText('feed').textContent).toContain('Newestidleno error')

    await act(async () => olderReload.resolve(feedNamed('Stale')))

    expect(screen.getByLabelText('feed').textContent).toContain('Newestidleno error')
  })

  it('keeps the newer success when an older reload fails last', async () => {
    const olderReload = deferred<HomeFeed>()
    const newerReload = deferred<HomeFeed>()
    vi.mocked(getHomeFeed)
      .mockResolvedValueOnce(feed)
      .mockReturnValueOnce(olderReload.promise)
      .mockReturnValueOnce(newerReload.promise)

    render(
      <HomeFeedProvider>
        <Consumer name="feed" />
      </HomeFeedProvider>,
    )

    await screen.findByText('Lin')
    fireEvent.click(screen.getByRole('button', { name: 'Reload feed' }))
    fireEvent.click(screen.getByRole('button', { name: 'Reload feed' }))

    await act(async () => newerReload.resolve(feedNamed('Newest')))
    await screen.findByText('Newest')

    await act(async () => olderReload.reject(new Error('Stale failure')))

    expect(screen.getByLabelText('feed').textContent).toContain('Newestidleno error')
  })

  it('stays loading when an older reload settles before the newer reload', async () => {
    const olderReload = deferred<HomeFeed>()
    const newerReload = deferred<HomeFeed>()
    vi.mocked(getHomeFeed)
      .mockResolvedValueOnce(feed)
      .mockReturnValueOnce(olderReload.promise)
      .mockReturnValueOnce(newerReload.promise)

    render(
      <HomeFeedProvider>
        <Consumer name="feed" />
      </HomeFeedProvider>,
    )

    await screen.findByText('Lin')
    fireEvent.click(screen.getByRole('button', { name: 'Reload feed' }))
    fireEvent.click(screen.getByRole('button', { name: 'Reload feed' }))

    await act(async () => olderReload.resolve(feedNamed('Stale')))

    expect(screen.getByLabelText('feed').textContent).toContain('Linloadingno error')

    await act(async () => newerReload.resolve(feedNamed('Newest')))
    await waitFor(() => {
      expect(screen.getByLabelText('feed').textContent).toContain('Newestidleno error')
    })
  })
})

describe('useHomeFeed', () => {
  it('throws a clear error outside HomeFeedProvider', () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined)

    expect(() => render(<Consumer name="orphan" />)).toThrow(
      'useHomeFeed must be used within a HomeFeedProvider',
    )

    consoleError.mockRestore()
  })
})
