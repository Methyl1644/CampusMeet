// @vitest-environment jsdom

import { act, renderHook } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { createElement, type PropsWithChildren } from 'react'
import { describe, expect, it } from 'vitest'
import {
  readExploreState,
  updateExploreState,
  useExploreState,
  writeExploreState,
} from './exploreState'

function wrapper({ children }: PropsWithChildren) {
  return createElement(
    MemoryRouter,
    {
      initialEntries: ['/discover?activity_q=robotics&activity_page=4&group_q=debate&group_page=7'],
      future: { v7_startTransition: true, v7_relativeSplatPath: true },
    },
    children,
  )
}

describe('Explore URL state', () => {
  it('round-trips independent activity and group search criteria', () => {
    const source = new URLSearchParams(
      'view=group'
      + '&activity_q=robotics&activity_tags=ai%2Ccode&activity_date=upcoming'
      + '&activity_status=registration_open&activity_type=organization'
      + '&activity_campus=Xianlin&activity_sort=deadline&activity_page=3'
      + '&group_q=debate&group_tags=speaking&group_date=past'
      + '&group_status=closed&group_type=discussion'
      + '&group_campus=Gulou&group_sort=hot&group_page=6',
    )

    const state = readExploreState(source)

    expect(state).toEqual({
      view: 'group',
      activity: {
        query: 'robotics',
        tagIds: ['ai', 'code'],
        filters: {
          date: 'upcoming',
          status: 'registration_open',
          type: 'organization',
          campus: 'Xianlin',
        },
        sort: 'deadline',
        page: 3,
      },
      group: {
        query: 'debate',
        tagIds: ['speaking'],
        filters: {
          date: 'past',
          status: 'closed',
          type: 'discussion',
          campus: 'Gulou',
        },
        sort: 'hot',
        page: 6,
      },
    })
    expect(readExploreState(writeExploreState(state.view, state))).toEqual(state)
  })

  it('normalizes unknown values, malformed pages, and duplicate tags to safe defaults', () => {
    const state = readExploreState(new URLSearchParams(
      'view=calendar&activity_tags=ai%2C%2Cai%2Ccode'
      + '&activity_date=tomorrow&activity_status=deleted&activity_type=private'
      + '&activity_sort=random&activity_page=0'
      + '&group_date=soon&group_status=archived&group_type=secret'
      + '&group_sort=popular&group_page=2.5',
    ))

    expect(state.view).toBe('activity')
    expect(state.activity).toEqual({
      query: '',
      tagIds: ['ai', 'code'],
      filters: { date: '', status: '', type: '', campus: '' },
      sort: 'latest',
      page: 1,
    })
    expect(state.group).toEqual({
      query: '',
      tagIds: [],
      filters: { date: '', status: '', type: '', campus: '' },
      sort: 'latest',
      page: 1,
    })
  })

  it('resets only the active page when search criteria change', () => {
    const original = readExploreState(new URLSearchParams(
      'view=activity&activity_page=5&group_page=8&group_status=full',
    ))

    const activityChanged = updateExploreState(original, {
      filters: { campus: 'Xianlin' },
    })
    expect(activityChanged.activity.page).toBe(1)
    expect(activityChanged.group.page).toBe(8)
    expect(activityChanged.group.filters.status).toBe('full')

    const groupActive = { ...activityChanged, view: 'group' as const }
    const groupChanged = updateExploreState(groupActive, { tagIds: ['music'] })
    expect(groupChanged.activity.page).toBe(1)
    expect(groupChanged.group.page).toBe(1)
    expect(groupChanged.group.tagIds).toEqual(['music'])
  })

  it('lets the hook switch views and update the active branch without losing the other branch', () => {
    const { result } = renderHook(() => {
      const explore = useExploreState()
      const location = useLocation()
      return { ...explore, search: location.search }
    }, { wrapper })

    act(() => result.current.updateActiveState({ filters: { status: 'registration_open' } }))
    expect(result.current.state.activity.page).toBe(1)
    expect(result.current.state.group.page).toBe(7)

    act(() => result.current.setView('group'))
    act(() => result.current.updateActiveState({ query: 'music' }))

    expect(result.current.state.view).toBe('group')
    expect(result.current.state.activity.query).toBe('robotics')
    expect(result.current.state.group.query).toBe('music')
    expect(result.current.state.group.page).toBe(1)
    expect(readExploreState(new URLSearchParams(result.current.search))).toEqual(result.current.state)
  })
})
