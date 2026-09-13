import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import GroupCard from '@/components/explore/GroupCard'
import CollectionPage from '@/components/personal/CollectionPage'
import CollectionTabs from '@/components/personal/CollectionTabs'
import { getMyGroups } from '@/api/personal'
import { setGroupFavorite } from '@/api/explore'
import { useToast } from '@/components/Toast'
import type { ExploreGroupCard, MyGroupView } from '@shared/types'

const tabs = [
  { value: 'joined', label: '已加入' },
  { value: 'pending', label: '申请中' },
  { value: 'saved', label: '已收藏' },
  { value: 'archived', label: '已归档' },
] satisfies Array<{ value: MyGroupView; label: string }>

export default function MyGroups() {
  const [search, setSearch] = useSearchParams()
  const requested = search.get('view') as MyGroupView | null
  const view = tabs.some((tab) => tab.value === requested) ? requested! : 'joined'
  const [items, setItems] = useState<ExploreGroupCard[]>([])
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
      const result = await getMyGroups(view, nextPage, 20)
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
      const result = await setGroupFavorite(id, value)
      setItems((current) => current.map((item) => item.id === id ? { ...item, bookmark: result.bookmark } : item))
      if (view === 'saved' && !result.bookmark) setItems((current) => current.filter((item) => item.id !== id))
    } catch {
      showToast('收藏状态更新失败', 'error')
    } finally {
      setPending((current) => { const next = new Set(current); next.delete(id); return next })
    }
  }

  return (
    <CollectionPage
      eyebrow="个人收藏"
      title="我的小组"
      description="查看已经加入、正在申请、收藏和归档的小团体与组队。"
      tabs={<CollectionTabs label="我的小组分类" tabs={tabs} value={view} onChange={(next) => setSearch({ view: next }, { replace: true })} />}
      loading={loading}
      error={error}
      empty={items.length === 0}
      hasMore={page < pages}
      loadingMore={loadingMore}
      onRetry={() => void load()}
      onLoadMore={() => void load(page + 1, true)}
    >
      <div role="tabpanel" className="mt-6 grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
        {items.map((item) => <GroupCard key={item.id} group={item} favoritePending={pending.has(item.id)} onFavorite={favorite} />)}
      </div>
    </CollectionPage>
  )
}
