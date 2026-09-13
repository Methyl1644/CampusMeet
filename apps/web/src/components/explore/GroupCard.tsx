import { useState } from 'react'
import { CalendarClock, Heart, Image, UserRound, UsersRound } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { ExploreGroupCard } from '@shared/types'

interface GroupCardProps {
  group: ExploreGroupCard
  favoritePending: boolean
  onFavorite: (id: string, favorite: boolean) => void
}

const purposeLabels = {
  team_recruitment: '招募队友',
  official_signup: '官方报名',
  discussion: '讨论',
} as const

function formatDeadline(value: string | null) {
  if (!value) return '截止时间待定'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '截止时间待定'
  return `${new Intl.DateTimeFormat('zh-CN', { month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false }).format(date)} 截止`
}

export default function GroupCard({ group, favoritePending, onFavorite }: GroupCardProps) {
  const [failedCoverUrl, setFailedCoverUrl] = useState<string | null>(null)
  const showCover = Boolean(group.cover_url) && failedCoverUrl !== group.cover_url
  const roles = [...group.needed_roles].sort((left, right) => left.localeCompare(right, 'zh-CN')).slice(0, 3)

  return (
    <article aria-label={group.title} className="group flex h-[444px] min-w-0 flex-col overflow-hidden rounded-card border border-stone bg-paper shadow-panel transition duration-feedback motion-safe:hover:-translate-y-0.5 hover:border-primary-300 hover:shadow-md">
      <div data-testid="group-media" className="relative aspect-[16/9] w-full shrink-0 overflow-hidden rounded-t-[12px] bg-[#EEF0F4]">
        {showCover ? (
          <img src={group.cover_url ?? undefined} alt={`${group.title}封面`} onError={() => setFailedCoverUrl(group.cover_url)} className="size-full object-cover transition-transform duration-feedback motion-safe:group-hover:scale-[1.02]" />
        ) : (
          <span role="img" aria-label="组队封面占位图" className="flex size-full items-center justify-center bg-[#E8EDF2] text-[#31576B]"><Image aria-hidden="true" className="size-9" /></span>
        )}
        <span className="absolute left-2.5 top-2.5 rounded-full bg-[#18362E]/90 px-2.5 py-1 text-xs font-semibold text-white">{purposeLabels[group.purpose]}</span>
        <button
          type="button"
          aria-label={`${group.bookmark ? '取消收藏' : '收藏'}${group.title}`}
          title={group.bookmark ? '取消收藏' : '收藏'}
          disabled={favoritePending}
          onClick={() => onFavorite(group.id, !group.bookmark)}
          className="absolute right-2.5 top-2.5 inline-flex size-10 items-center justify-center rounded-full border border-white/80 bg-paper/95 text-primary-700 shadow-panel transition-colors duration-feedback hover:bg-primary-50"
        >
          <Heart aria-hidden="true" className="size-[18px]" fill={group.bookmark ? 'currentColor' : 'none'} />
        </button>
      </div>

      <div className="flex min-h-0 flex-1 flex-col p-4">
        <h2 className="line-clamp-2 h-12 text-base font-bold leading-6 text-ink">{group.title}</h2>
        <p className="mt-2 flex h-5 items-center gap-1.5 truncate text-xs font-semibold text-primary-700"><CalendarClock aria-hidden="true" className="size-4 shrink-0" />{formatDeadline(group.deadline)}</p>
        <div className="mt-2 flex h-5 items-center gap-3 text-xs text-ink-muted">
          <span className="flex min-w-0 items-center gap-1"><UserRound aria-hidden="true" className="size-3.5 shrink-0" /><span className="truncate">{group.author ? `${group.author.nickname}发起` : '发起人待确认'}</span></span>
          <span className="flex shrink-0 items-center gap-1"><UsersRound aria-hidden="true" className="size-3.5" />{group.current_members} / {group.target_members} 人</span>
        </div>
        <div className="mt-3 flex h-7 gap-1.5 overflow-hidden" aria-label="所需角色">
          {roles.length > 0 ? roles.map((role) => <span key={role} className="truncate rounded-full bg-[#EEF2F3] px-2.5 py-1 text-xs font-medium text-ink-muted">{role}</span>) : <span className="text-xs text-ink-muted">角色不限</span>}
        </div>
        {group.linked_activity && (
          <Link to={`/topics/${group.linked_activity.id}`} className="mt-3 block h-5 truncate text-xs font-semibold text-primary-700 hover:text-primary-800">关联活动：{group.linked_activity.short_title}</Link>
        )}
        <div className="mt-auto border-t border-stone pt-3">
          <Link to={`/posts/${group.id}`} aria-label="查看组队详情" className="inline-flex min-h-9 items-center text-sm font-semibold text-primary-700 transition-colors duration-feedback hover:text-primary-800">查看组队详情</Link>
        </div>
      </div>
    </article>
  )
}
