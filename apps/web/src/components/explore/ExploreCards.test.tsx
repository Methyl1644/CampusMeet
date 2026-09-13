// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ReactNode } from 'react'
import { MemoryRouter } from 'react-router-dom'
import ActivityCard from './ActivityCard'
import GroupCard from './GroupCard'
import { activityFixture, groupFixture } from './exploreTestFixtures'

function renderCard(node: ReactNode) {
  return render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      {node}
    </MemoryRouter>,
  )
}

afterEach(cleanup)

describe('Explore result cards', () => {
  it('keeps activity media geometry stable and exposes its scan metadata and actions', () => {
    const onFavorite = vi.fn()
    renderCard(<ActivityCard activity={activityFixture} onFavorite={onFavorite} favoritePending={false} />)

    const card = screen.getByRole('article', { name: activityFixture.title })
    const media = within(card).getByTestId('activity-media')
    expect(media.classList.contains('aspect-[16/9]')).toBe(true)
    expect(within(media).getByRole('img').getAttribute('src')).toBe(activityFixture.cover_url)
    expect(within(card).getByText(/10月3日/)).toBeTruthy()
    expect(within(card).getByText(/9月25日.*报名截止/)).toBeTruthy()
    expect(within(card).getByText(activityFixture.organizer)).toBeTruthy()
    expect(within(card).getByText('仙林校区')).toBeTruthy()
    expect(within(card).getByText('31 人参加')).toBeTruthy()
    expect(within(card).getByText('剩余 9 个名额')).toBeTruthy()
    expect(within(card).getByRole('link', { name: '查看活动详情' }).getAttribute('href')).toBe('/topics/activity-1')

    fireEvent.click(within(card).getByRole('button', { name: `收藏${activityFixture.title}` }))
    expect(onFavorite).toHaveBeenCalledWith(activityFixture.id, true)
  })

  it('uses a stable labelled placeholder when an activity has no cover', () => {
    renderCard(
      <ActivityCard
        activity={{ ...activityFixture, id: 'activity-placeholder', cover_url: null }}
        onFavorite={vi.fn()}
        favoritePending={false}
      />,
    )

    const media = screen.getByTestId('activity-media')
    expect(media.classList.contains('aspect-[16/9]')).toBe(true)
    expect(within(media).getByRole('img', { name: '活动封面占位图' })).toBeTruthy()
  })

  it('shows group purpose, timing, owner, capacity, roles, linked activity, and persistent actions', () => {
    const onFavorite = vi.fn()
    renderCard(<GroupCard group={groupFixture} onFavorite={onFavorite} favoritePending={false} />)

    const card = screen.getByRole('article', { name: groupFixture.title })
    const media = within(card).getByTestId('group-media')
    expect(media.classList.contains('aspect-[16/9]')).toBe(true)
    expect(within(media).getByRole('img', { name: '组队封面占位图' })).toBeTruthy()
    expect(within(card).getByText('招募队友')).toBeTruthy()
    expect(within(card).getByText(/9月28日/)).toBeTruthy()
    expect(within(card).getByText('林晓发起')).toBeTruthy()
    expect(within(card).getByText('3 / 5 人')).toBeTruthy()
    expect(within(card).getByText('前端开发')).toBeTruthy()
    expect(within(card).getByText('视觉设计')).toBeTruthy()
    expect(within(card).getByRole('link', { name: new RegExp(activityFixture.short_title) }).getAttribute('href')).toBe('/topics/activity-1')
    expect(within(card).getByRole('link', { name: '查看组队详情' }).getAttribute('href')).toBe('/posts/group-1')

    fireEvent.click(within(card).getByRole('button', { name: `收藏${groupFixture.title}` }))
    expect(onFavorite).toHaveBeenCalledWith(groupFixture.id, true)
  })
})
