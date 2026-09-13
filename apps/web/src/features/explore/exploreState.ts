import { useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'

export type ExploreView = 'activity' | 'group'
export type ExploreSort = 'latest' | 'hot' | 'deadline'
export type ExploreDateFilter = '' | 'upcoming' | 'registration_open' | 'past'
export type ActivityStatusFilter = '' | 'registration_open' | 'ended'
export type GroupStatusFilter = '' | 'recruiting' | 'full' | 'closed'
export type ActivityTypeFilter =
  | ''
  | 'official'
  | 'organization'
  | 'open_team'
  | 'official_signup'
  | 'information_only'
export type GroupTypeFilter =
  | ''
  | 'team_recruitment'
  | 'official_signup'
  | 'discussion'
  | 'topic_team'
  | 'casual_invitation'

export interface ActivityExploreState {
  query: string
  tagIds: string[]
  filters: {
    date: ExploreDateFilter
    status: ActivityStatusFilter
    type: ActivityTypeFilter
    campus: string
  }
  sort: ExploreSort
  page: number
}

export interface GroupExploreState {
  query: string
  tagIds: string[]
  filters: {
    date: Exclude<ExploreDateFilter, 'registration_open'>
    status: GroupStatusFilter
    type: GroupTypeFilter
    campus: string
  }
  sort: ExploreSort
  page: number
}

export interface ExploreState {
  view: ExploreView
  activity: ActivityExploreState
  group: GroupExploreState
}

type ExploreFilters = ActivityExploreState['filters'] | GroupExploreState['filters']

export interface ExploreViewStateUpdate {
  query?: string
  tagIds?: string[]
  filters?: Partial<ExploreFilters>
  sort?: ExploreSort
  page?: number
}

const sorts = new Set<ExploreSort>(['latest', 'hot', 'deadline'])
const activityDates = new Set<ActivityExploreState['filters']['date']>([
  '', 'upcoming', 'registration_open', 'past',
])
const groupDates = new Set<GroupExploreState['filters']['date']>(['', 'upcoming', 'past'])
const activityStatuses = new Set<ActivityStatusFilter>(['', 'registration_open', 'ended'])
const groupStatuses = new Set<GroupStatusFilter>(['', 'recruiting', 'full', 'closed'])
const activityTypes = new Set<ActivityTypeFilter>([
  '', 'official', 'organization', 'open_team', 'official_signup', 'information_only',
])
const groupTypes = new Set<GroupTypeFilter>([
  '', 'team_recruitment', 'official_signup', 'discussion', 'topic_team', 'casual_invitation',
])

function oneOf<T extends string>(value: string | null, values: ReadonlySet<T>, fallback: T): T {
  return value !== null && values.has(value as T) ? value as T : fallback
}

function pageValue(value: string | null): number {
  if (!value || !/^\d+$/.test(value)) return 1
  const page = Number(value)
  return Number.isSafeInteger(page) && page >= 1 ? page : 1
}

function tagsValue(value: string | null): string[] {
  if (!value) return []
  return [...new Set(value.split(',').map((tag) => tag.trim()).filter(Boolean))]
}

function readActivity(search: URLSearchParams): ActivityExploreState {
  return {
    query: search.get('activity_q') ?? '',
    tagIds: tagsValue(search.get('activity_tags')),
    filters: {
      date: oneOf(search.get('activity_date'), activityDates, ''),
      status: oneOf(search.get('activity_status'), activityStatuses, ''),
      type: oneOf(search.get('activity_type'), activityTypes, ''),
      campus: search.get('activity_campus') ?? '',
    },
    sort: oneOf(search.get('activity_sort'), sorts, 'latest'),
    page: pageValue(search.get('activity_page')),
  }
}

function readGroup(search: URLSearchParams): GroupExploreState {
  return {
    query: search.get('group_q') ?? '',
    tagIds: tagsValue(search.get('group_tags')),
    filters: {
      date: oneOf(search.get('group_date'), groupDates, ''),
      status: oneOf(search.get('group_status'), groupStatuses, ''),
      type: oneOf(search.get('group_type'), groupTypes, ''),
      campus: search.get('group_campus') ?? '',
    },
    sort: oneOf(search.get('group_sort'), sorts, 'latest'),
    page: pageValue(search.get('group_page')),
  }
}

export function readExploreState(search: URLSearchParams): ExploreState {
  return {
    view: search.get('view') === 'group' ? 'group' : 'activity',
    activity: readActivity(search),
    group: readGroup(search),
  }
}

function setNonDefault(search: URLSearchParams, key: string, value: string, fallback = '') {
  if (value !== fallback) search.set(key, value)
}

function writeViewState(
  search: URLSearchParams,
  prefix: ExploreView,
  state: ActivityExploreState | GroupExploreState,
) {
  setNonDefault(search, `${prefix}_q`, state.query)
  setNonDefault(search, `${prefix}_tags`, state.tagIds.join(','))
  setNonDefault(search, `${prefix}_date`, state.filters.date)
  setNonDefault(search, `${prefix}_status`, state.filters.status)
  setNonDefault(search, `${prefix}_type`, state.filters.type)
  setNonDefault(search, `${prefix}_campus`, state.filters.campus)
  setNonDefault(search, `${prefix}_sort`, state.sort, 'latest')
  if (state.page !== 1) search.set(`${prefix}_page`, String(state.page))
}

export function writeExploreState(view: ExploreView, state: ExploreState): URLSearchParams {
  const search = new URLSearchParams()
  if (view === 'group') search.set('view', view)
  writeViewState(search, 'activity', state.activity)
  writeViewState(search, 'group', state.group)
  return search
}

function sameTags(left: string[], right: string[]): boolean {
  return left.length === right.length && left.every((tag, index) => tag === right[index])
}

function sameFilters(left: ExploreFilters, right: ExploreFilters): boolean {
  return left.date === right.date
    && left.status === right.status
    && left.type === right.type
    && left.campus === right.campus
}

function updateActivity(
  current: ActivityExploreState,
  update: ExploreViewStateUpdate,
): ActivityExploreState {
  const merged: ActivityExploreState = {
    query: update.query ?? current.query,
    tagIds: update.tagIds ? [...new Set(update.tagIds.map((tag) => tag.trim()).filter(Boolean))] : current.tagIds,
    filters: {
      date: update.filters?.date !== undefined
        ? oneOf(update.filters.date, activityDates, '')
        : current.filters.date,
      status: update.filters?.status !== undefined
        ? oneOf(update.filters.status, activityStatuses, '')
        : current.filters.status,
      type: update.filters?.type !== undefined
        ? oneOf(update.filters.type, activityTypes, '')
        : current.filters.type,
      campus: update.filters?.campus ?? current.filters.campus,
    },
    sort: update.sort ?? current.sort,
    page: update.page !== undefined && Number.isSafeInteger(update.page) && update.page >= 1
      ? update.page
      : current.page,
  }
  const criteriaChanged = merged.query !== current.query
    || !sameTags(merged.tagIds, current.tagIds)
    || !sameFilters(merged.filters, current.filters)
    || merged.sort !== current.sort
  return criteriaChanged ? { ...merged, page: 1 } : merged
}

function updateGroup(current: GroupExploreState, update: ExploreViewStateUpdate): GroupExploreState {
  const merged: GroupExploreState = {
    query: update.query ?? current.query,
    tagIds: update.tagIds ? [...new Set(update.tagIds.map((tag) => tag.trim()).filter(Boolean))] : current.tagIds,
    filters: {
      date: update.filters?.date !== undefined
        ? oneOf(update.filters.date, groupDates, '')
        : current.filters.date,
      status: update.filters?.status !== undefined
        ? oneOf(update.filters.status, groupStatuses, '')
        : current.filters.status,
      type: update.filters?.type !== undefined
        ? oneOf(update.filters.type, groupTypes, '')
        : current.filters.type,
      campus: update.filters?.campus ?? current.filters.campus,
    },
    sort: update.sort ?? current.sort,
    page: update.page !== undefined && Number.isSafeInteger(update.page) && update.page >= 1
      ? update.page
      : current.page,
  }
  const criteriaChanged = merged.query !== current.query
    || !sameTags(merged.tagIds, current.tagIds)
    || !sameFilters(merged.filters, current.filters)
    || merged.sort !== current.sort
  return criteriaChanged ? { ...merged, page: 1 } : merged
}

export function updateExploreState(
  state: ExploreState,
  update: ExploreViewStateUpdate,
): ExploreState {
  return state.view === 'activity'
    ? { ...state, activity: updateActivity(state.activity, update) }
    : { ...state, group: updateGroup(state.group, update) }
}

export function useExploreState() {
  const [search, setSearch] = useSearchParams()
  const state = useMemo(() => readExploreState(search), [search])

  const setView = useCallback((view: ExploreView) => {
    setSearch((currentSearch) => {
      const current = readExploreState(currentSearch)
      return writeExploreState(view, { ...current, view })
    })
  }, [setSearch])

  const updateActiveState = useCallback((update: ExploreViewStateUpdate) => {
    const replace = update.page === undefined
      || update.query !== undefined
      || update.tagIds !== undefined
      || update.filters !== undefined
      || update.sort !== undefined
    setSearch((currentSearch) => {
      const next = updateExploreState(readExploreState(currentSearch), update)
      return writeExploreState(next.view, next)
    }, { replace })
  }, [setSearch])

  const replaceActivePage = useCallback((page: number) => {
    setSearch((currentSearch) => {
      const next = updateExploreState(readExploreState(currentSearch), { page })
      return writeExploreState(next.view, next)
    }, { replace: true })
  }, [setSearch])

  return {
    state,
    activeState: state[state.view],
    setView,
    updateActiveState,
    replaceActivePage,
  }
}
