import { useEffect, useState } from 'react'
import { ArrowUpRight, MessageCircle, RefreshCw, UsersRound } from 'lucide-react'
import { Link } from 'react-router-dom'
import { listRelatedGroups } from '@/api/explore'
import type { ExploreGroupCard, ParticipationMode, PostPurpose } from '@shared/types'

const purposeLabels: Record<PostPurpose, string> = {
  team_recruitment: '招募队友',
  official_signup: '官方报名',
  discussion: '讨论',
}

const tabs: Array<{ purpose: PostPurpose; label: string }> = [
  { purpose: 'team_recruitment', label: '组队招募' },
  { purpose: 'official_signup', label: '官方报名' },
  { purpose: 'discussion', label: '相关讨论' },
]

const purposeForMode: Record<ParticipationMode, PostPurpose> = {
  open_team: 'team_recruitment',
  official_signup: 'official_signup',
  information_only: 'discussion',
}

const emptyCopy: Record<PostPurpose, string> = {
  team_recruitment: '还没有相关组队，成为第一个发起人。',
  official_signup: '官方报名入口暂未发布，请关注活动更新。',
  discussion: '暂时没有相关讨论。',
}

const pageSize = 8

export default function RelatedGroups({
  topicId,
  groups,
  mode,
}: {
  topicId: string
  groups: ExploreGroupCard[]
  mode: ParticipationMode
}) {
  const defaultPurpose = purposeForMode[mode]
  const [purpose, setPurpose] = useState<PostPurpose>(defaultPurpose)
  const [items, setItems] = useState(() => groups.filter((group) => group.purpose === defaultPurpose).slice(0, pageSize))
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    setPurpose(defaultPurpose)
  }, [defaultPurpose, topicId])

  useEffect(() => {
    let active = true
    const initialItems = groups.filter((group) => group.purpose === purpose).slice(0, pageSize)
    setItems(initialItems)
    setPage(1)
    setPages(1)
    setError('')
    setLoading(true)
    void listRelatedGroups(topicId, { purpose, page: 1, pageSize })
      .then((result) => {
        if (!active) return
        setItems(result.list)
        setPage(result.page)
        setPages(result.pages)
      })
      .catch(() => {
        if (active) setError('关联内容加载失败，请重试。')
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => { active = false }
  }, [groups, purpose, reloadKey, topicId])

  const loadMore = async () => {
    if (loading || page >= pages) return
    setLoading(true)
    setError('')
    try {
      const result = await listRelatedGroups(topicId, { purpose, page: page + 1, pageSize })
      setItems((current) => [...current, ...result.list.filter((item) => !current.some((existing) => existing.id === item.id))])
      setPage(result.page)
      setPages(result.pages)
    } catch {
      setError('关联内容加载失败，请重试。')
    } finally {
      setLoading(false)
    }
  }

  return (
    <section id="related-groups" aria-labelledby="related-groups-title" className="scroll-mt-28 border-t border-stone pt-7">
      <p className="section-label">继续参与</p>
      <h2 id="related-groups-title" className="mt-2 text-xl font-bold text-ink">活动相关内容</h2>
      <div role="tablist" aria-label="关联内容分类" className="mt-4 flex gap-2 overflow-x-auto border-b border-stone pb-3">
        {tabs.map((tab) => (
          <button
            key={tab.purpose}
            type="button"
            role="tab"
            aria-selected={purpose === tab.purpose}
            className={purpose === tab.purpose ? 'btn-primary min-h-10 shrink-0' : 'btn-secondary min-h-10 shrink-0'}
            onClick={() => setPurpose(tab.purpose)}
          >
            {tab.label}
          </button>
        ))}
      </div>
      {items.length > 0 ? (
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {items.map((group) => (
            <article key={group.id} className="flex min-w-0 flex-col rounded-card border border-stone bg-paper p-4">
              <div className="flex items-center justify-between gap-3">
                <span className="rounded-full bg-[#EAF3F0] px-2.5 py-1 text-xs font-semibold text-campus-green">{purposeLabels[group.purpose]}</span>
                <span className="inline-flex shrink-0 items-center gap-1 text-xs text-ink-muted"><UsersRound aria-hidden="true" className="size-3.5" />{group.current_members}/{group.target_members}</span>
              </div>
              <h3 className="mt-3 break-words text-base font-bold leading-6 text-ink">{group.title}</h3>
              <p className="mt-2 line-clamp-2 text-sm leading-6 text-ink-muted">{group.description || '暂无补充说明'}</p>
              <Link to={`/posts/${group.id}`} className="mt-4 inline-flex min-h-9 items-center gap-1 self-start text-sm font-semibold text-primary-700 hover:text-primary-800">
                查看详情<ArrowUpRight aria-hidden="true" className="size-4" />
              </Link>
            </article>
          ))}
        </div>
      ) : !loading && !error ? (
        <div className="mt-4 flex items-start gap-2 border-y border-stone py-6 text-sm text-ink-muted">
          <MessageCircle aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
          <p>{emptyCopy[purpose]}</p>
        </div>
      ) : null}
      {loading && <p role="status" className="mt-4 text-sm text-ink-muted">正在加载关联内容...</p>}
      {error && <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-y border-red-200 bg-red-50 px-3 py-3 text-sm text-red-700"><span>{error}</span><button type="button" className="btn-secondary min-h-9" onClick={() => setReloadKey((value) => value + 1)}><RefreshCw aria-hidden="true" className="size-4" />重试</button></div>}
      {page < pages && !error && <button type="button" className="btn-secondary mt-4" disabled={loading} onClick={() => void loadMore()}>{loading ? '加载中...' : '加载更多'}</button>}
    </section>
  )
}
