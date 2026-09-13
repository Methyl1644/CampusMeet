import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import ActivityCard from '@/components/explore/ActivityCard'
import CollectionPage from '@/components/personal/CollectionPage'
import CollectionTabs from '@/components/personal/CollectionTabs'
import { getMyActivities } from '@/api/personal'
import { setActivityFavorite } from '@/api/explore'
import { useToast } from '@/components/Toast'
import type { ExploreActivityCard, MyActivityView } from '@shared/types'

const tabs = [
  { value: 'attending', label: '参加中' },
  { value: 'saved', label: '已收藏' },
  { value: 'past', label: '已结束' },
] satisfies Array<{ value: MyActivityView; label: string }>

export default function MyActivities() {
  const [search, setSearch] = useSearchParams()
  const requested = search.get('view') as MyActivityView | null
  const view = tabs.some((tab) => tab.value === requested) ? requested! : 'attending'
  const [items, setItems] = useState<ExploreActivityCard[]>([])
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState(false)
  const [pending, setPending] = useState<Set<string>>(() => new Set())
  const { showToast } = useToast()

  const load = useCallback(async (nextPage = 1, append = false) => {
    append ? setLoadingMore(true) : setLoading(true)
    setError(false)
    try {
      const result = await getMyActivities(view, nextPage, 20)
      setItems((current) => append ? [...current, ...result.list.filter((item) => !current.some((known) => known.id === item.id))] : result.list)
      setPage(result.page)
      setPages(result.pages)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
      setLoadingMore(false)
    }
  }, [view])

  useEffect(() => { void load() }, [load])

  const favorite = async (id: string, value: boolean) => {
    setPending((current) => new Set(current).add(id))
    try {
      const result = await setActivityFavorite(id, value)
      setItems((current) => current.map((item) => item.id === id ? { ...item, favorite: result.favorite, followed: result.followed, follower_count: result.follower_count } : item))
      if (view === 'saved' && !result.favorite) setItems((current) => current.filter((item) => item.id !== id))
    } catch {
      showToast('收藏状态更新失败', 'error')
    } finally {
      setPending((current) => { const next = new Set(current); next.delete(id); return next })
    }
  }

  return (
    <CollectionPage
      eyebrow="个人收藏"
      title="我的活动"
      description="集中查看正在参加、已经收藏和已经结束的正式活动。"
      tabs={<CollectionTabs label="我的活动分类" tabs={tabs} value={view} onChange={(next) => setSearch({ view: next }, { replace: true })} />}
      loading={loading}
      error={error}
      empty={items.length === 0}
      hasMore={page < pages}
      loadingMore={loadingMore}
      onRetry={() => void load()}
      onLoadMore={() => void load(page + 1, true)}
    >
      <div role="tabpanel" className="mt-6 grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
        {items.map((item) => <ActivityCard key={item.id} activity={item} favoritePending={pending.has(item.id)} onFavorite={favorite} />)}
      </div>
    </CollectionPage>
  )
}
