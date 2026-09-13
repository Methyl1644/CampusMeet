import { useCallback, useEffect, useState } from 'react'
import { AlertCircle, ChevronLeft, ChevronRight, Search, X } from 'lucide-react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import type { ExploreActivityCard, ExploreGroupCard, ExplorePage } from '@shared/types'
import {
  listExploreActivities,
  listExploreGroups,
  setActivityFavorite,
  setGroupFavorite,
} from '@/api/explore'
import CategoryRail from '@/components/explore/CategoryRail'
import ExploreFilters from '@/components/explore/ExploreFilters'
import ExploreGrid from '@/components/explore/ExploreGrid'
import ExploreSkeleton from '@/components/explore/ExploreSkeleton'
import ExploreSwitcher from '@/components/explore/ExploreSwitcher'
import { useToast } from '@/components/Toast'
import { useExploreState, type ExploreView } from '@/features/explore/exploreState'

const PAGE_SIZE = 12
const headings = {
  activity: '发现值得认真准备的校园活动',
  group: '找到此刻正缺你的队伍',
} as const
const descriptions = {
  activity: '浏览校方与认证组织发布的正式活动，提前了解时间、范围与参与方式。',
  group: '发现同学发起的招募与讨论，找到目标、时间和角色都合适的伙伴。',
} as const

interface ResultsState {
  activities: ExplorePage<ExploreActivityCard> | null
  groups: ExplorePage<ExploreGroupCard> | null
  loading: boolean
  error: boolean
}

function emptyResults(): ResultsState {
  return { activities: null, groups: null, loading: true, error: false }
}

export default function DiscoveryHub() {
  const { state, activeState, setView, updateActiveState } = useExploreState()
  const { showToast } = useToast()
  const shouldReduceMotion = useReducedMotion()
  const [results, setResults] = useState<ResultsState>(emptyResults)
  const [retryGeneration, setRetryGeneration] = useState(0)
  const [favoritePending, setFavoritePending] = useState<Set<string>>(() => new Set())

  useEffect(() => {
    const controller = new AbortController()
    setResults((current) => ({ ...current, loading: true, error: false }))

    const load = async () => {
      try {
        if (state.view === 'activity') {
          const page = await listExploreActivities({
            query: state.activity.query || undefined,
            tagIds: state.activity.tagIds.length ? state.activity.tagIds : undefined,
            date: state.activity.filters.date || undefined,
            status: state.activity.filters.status || undefined,
            type: state.activity.filters.type || undefined,
            campus: state.activity.filters.campus || undefined,
            page: state.activity.page,
            pageSize: PAGE_SIZE,
          }, controller.signal)
          setResults((current) => ({ ...current, activities: page, loading: false, error: false }))
        } else {
          const page = await listExploreGroups({
            query: state.group.query || undefined,
            tagIds: state.group.tagIds.length ? state.group.tagIds : undefined,
            date: state.group.filters.date || undefined,
            status: state.group.filters.status || undefined,
            type: state.group.filters.type || undefined,
            campus: state.group.filters.campus || undefined,
            page: state.group.page,
            pageSize: PAGE_SIZE,
          }, controller.signal)
          setResults((current) => ({ ...current, groups: page, loading: false, error: false }))
        }
      } catch {
        if (!controller.signal.aborted) setResults((current) => ({ ...current, loading: false, error: true }))
      }
    }

    void load()
    return () => controller.abort()
  }, [state.view, state.activity, state.group, retryGeneration])

  const changeView = (view: ExploreView) => {
    if (view !== state.view) setView(view)
  }

  const markFavoritePending = (key: string, pending: boolean) => {
    setFavoritePending((current) => {
      const next = new Set(current)
      if (pending) next.add(key)
      else next.delete(key)
      return next
    })
  }

  const favoriteActivity = useCallback(async (id: string, favorite: boolean) => {
    const key = `activity:${id}`
    const previous = results.activities?.list.find((item) => item.id === id)
    if (!previous || favoritePending.has(key)) return
    markFavoritePending(key, true)
    setResults((current) => current.activities ? {
      ...current,
      activities: {
        ...current.activities,
        list: current.activities.list.map((item) => item.id === id ? {
          ...item,
          favorite,
          followed: favorite,
          follower_count: Math.max(0, item.follower_count + (favorite ? 1 : -1)),
        } : item),
      },
    } : current)
    try {
      const updated = await setActivityFavorite(id, favorite)
      setResults((current) => current.activities ? {
        ...current,
        activities: {
          ...current.activities,
          list: current.activities.list.map((item) => item.id === id ? {
            ...item,
            favorite: updated.favorite,
            followed: updated.followed,
            follower_count: updated.follower_count,
          } : item),
        },
      } : current)
    } catch {
      setResults((current) => current.activities ? {
        ...current,
        activities: {
          ...current.activities,
          list: current.activities.list.map((item) => item.id === id ? {
            ...item,
            favorite: previous.favorite,
            followed: previous.followed,
            follower_count: previous.follower_count,
          } : item),
        },
      } : current)
      showToast('收藏失败，已恢复原状态', 'error')
    } finally {
      markFavoritePending(key, false)
    }
  }, [favoritePending, results.activities, showToast])

  const favoriteGroup = useCallback(async (id: string, favorite: boolean) => {
    const key = `group:${id}`
    const previous = results.groups?.list.find((item) => item.id === id)
    if (!previous || favoritePending.has(key)) return
    markFavoritePending(key, true)
    setResults((current) => current.groups ? {
      ...current,
      groups: { ...current.groups, list: current.groups.list.map((item) => item.id === id ? { ...item, bookmark: favorite } : item) },
    } : current)
    try {
      const updated = await setGroupFavorite(id, favorite)
      setResults((current) => current.groups ? {
        ...current,
        groups: { ...current.groups, list: current.groups.list.map((item) => item.id === id ? { ...item, bookmark: updated.bookmark } : item) },
      } : current)
    } catch {
      setResults((current) => current.groups ? {
        ...current,
        groups: {
          ...current.groups,
          list: current.groups.list.map((item) => item.id === id ? {
            ...item,
            bookmark: previous.bookmark,
          } : item),
        },
      } : current)
      showToast('收藏失败，已恢复原状态', 'error')
    } finally {
      markFavoritePending(key, false)
    }
  }, [favoritePending, results.groups, showToast])

  const page = state.view === 'activity' ? results.activities : results.groups
  const noun = state.view === 'activity' ? '活动' : '组队'
  const transition = { duration: shouldReduceMotion ? 0.1 : 0.2, ease: [0.22, 1, 0.36, 1] as const }

  return (
    <div className="min-w-0">
      <header className="border-b border-stone pb-5 md:pb-6">
        <ExploreSwitcher view={state.view} onChange={changeView} />
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={state.view}
            initial={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: -4 }}
            transition={transition}
            className="mt-6 max-w-3xl"
          >
            <h1 className="text-2xl font-bold leading-9 text-ink sm:text-3xl">{headings[state.view]}</h1>
            <p className="mt-2 text-sm leading-6 text-ink-muted">{descriptions[state.view]}</p>
          </motion.div>
        </AnimatePresence>

        <div className="relative mt-5 max-w-3xl">
          <Search aria-hidden="true" className="pointer-events-none absolute left-4 top-3.5 size-4 text-ink-muted" />
          <input
            type="search"
            value={activeState.query}
            onChange={(event) => updateActiveState({ query: event.target.value })}
            aria-label={`搜索${noun}`}
            placeholder={`搜索${noun}名称、组织者或标签`}
            className="input-base h-11 pl-11 pr-11"
          />
          {activeState.query && (
            <button type="button" onClick={() => updateActiveState({ query: '' })} className="icon-button absolute right-0.5 top-0.5" aria-label="清空搜索" title="清空搜索"><X aria-hidden="true" className="size-4" /></button>
          )}
        </div>

        <ExploreFilters view={state.view} state={activeState} onChange={updateActiveState} />
        <CategoryRail view={state.view} selectedTagIds={activeState.tagIds} onChange={(tagIds) => updateActiveState({ tagIds })} />
      </header>

      <section className="pt-5" aria-labelledby="explore-result-count">
        <div className="mb-4 flex min-h-7 items-center justify-between gap-4">
          <p id="explore-result-count" className="text-sm font-semibold text-ink">{page && !results.loading && !results.error ? `共 ${page.total} 个${noun}` : `探索${noun}`}</p>
          <span className="text-xs text-ink-muted">最新发布</span>
        </div>
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            id="explore-results"
            role="tabpanel"
            aria-labelledby={`explore-${state.view}-tab`}
            tabIndex={0}
            key={`${state.view}-${results.loading ? 'loading' : results.error ? 'error' : 'ready'}-${activeState.page}`}
            initial={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: -4 }}
            transition={transition}
          >
            {results.loading ? (
              <ExploreSkeleton view={state.view} />
            ) : results.error ? (
              <div role="alert" className="flex min-h-56 flex-col items-center justify-center border-y border-stone px-4 py-12 text-center">
                <AlertCircle aria-hidden="true" className="size-8 text-red-700" />
                <h2 className="mt-3 text-base font-bold text-ink">{noun}加载失败</h2>
                <p className="mt-1 text-sm text-ink-muted">请检查网络后重新加载。</p>
                <button type="button" onClick={() => setRetryGeneration((value) => value + 1)} className="btn-primary mt-4">重新加载</button>
              </div>
            ) : page && page.list.length > 0 ? (
              <>
                <ExploreGrid
                  view={state.view}
                  activities={results.activities?.list ?? []}
                  groups={results.groups?.list ?? []}
                  favoritePending={favoritePending}
                  onActivityFavorite={(id, favorite) => void favoriteActivity(id, favorite)}
                  onGroupFavorite={(id, favorite) => void favoriteGroup(id, favorite)}
                />
                {page.pages > 1 && (
                  <nav aria-label={`${noun}分页`} className="mt-7 flex min-h-11 items-center justify-center gap-4 border-t border-stone pt-6">
                    <button type="button" aria-label="上一页" disabled={page.page <= 1} onClick={() => updateActiveState({ page: page.page - 1 })} className="btn-secondary size-10 p-0"><ChevronLeft aria-hidden="true" className="size-4" /></button>
                    <span className="min-w-24 text-center text-sm font-medium text-ink">第 {page.page} / {page.pages} 页</span>
                    <button type="button" aria-label="下一页" disabled={page.page >= page.pages} onClick={() => updateActiveState({ page: page.page + 1 })} className="btn-secondary size-10 p-0"><ChevronRight aria-hidden="true" className="size-4" /></button>
                  </nav>
                )}
              </>
            ) : (
              <div className="flex min-h-56 flex-col items-center justify-center border-y border-stone px-4 py-12 text-center">
                <Search aria-hidden="true" className="size-8 text-ink-muted" />
                <h2 className="mt-3 text-base font-bold text-ink">没有找到符合条件的{noun}</h2>
                <p className="mt-1 text-sm text-ink-muted">试试清空搜索或调整筛选条件。</p>
              </div>
            )}
          </motion.div>
        </AnimatePresence>
      </section>
    </div>
  )
}
