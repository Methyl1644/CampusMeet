import { useState } from 'react'
import { CalendarDays, Heart, Image, MapPin, UsersRound } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { ExploreActivityCard } from '@shared/types'

interface ActivityCardProps {
  activity: ExploreActivityCard
  favoritePending: boolean
  onFavorite: (id: string, favorite: boolean) => void
  favoriteEnabled?: boolean
}

function formatDate(value: string | null) {
  if (!value) return '时间待公布'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '时间待公布'
  return new Intl.DateTimeFormat('zh-CN', {
    month: 'long', day: 'numeric', weekday: 'short', hour: '2-digit', minute: '2-digit', hour12: false,
  }).format(date)
}

function formatDeadline(value: string | null) {
  if (!value) return '报名截止待公布'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '报名截止待公布'
  return `${new Intl.DateTimeFormat('zh-CN', { month: 'long', day: 'numeric' }).format(date)} 报名截止`
}

function capacityLabel(activity: ExploreActivityCard) {
  if (activity.capacity === null) return `${activity.participant_count} 人参加`
  const remaining = Math.max(activity.capacity - activity.participant_count, 0)
  return remaining > 0 ? `剩余 ${remaining} 个名额` : '名额已满'
}

export default function ActivityCard({ activity, favoritePending, onFavorite, favoriteEnabled = true }: ActivityCardProps) {
  const favorite = activity.favorite || activity.followed
  const [failedCoverUrl, setFailedCoverUrl] = useState<string | null>(null)
  const showCover = Boolean(activity.cover_url) && failedCoverUrl !== activity.cover_url
  const tags = [...activity.tags].sort((left, right) => (
    left.canonical_name.localeCompare(right.canonical_name, 'zh-CN')
  )).slice(0, 2)

  return (
    <article aria-label={activity.title} className="group relative flex h-[432px] min-w-0 flex-col overflow-hidden rounded-card border border-stone bg-paper shadow-panel transition duration-feedback motion-safe:hover:-translate-y-0.5 hover:border-primary-300 hover:shadow-md">
      <div data-testid="activity-media" className="relative aspect-[16/9] w-full shrink-0 overflow-hidden rounded-t-[12px] bg-[#EDF1F4]">
        {showCover ? (
          <img src={activity.cover_url ?? undefined} alt={`${activity.title}封面`} onError={() => setFailedCoverUrl(activity.cover_url)} className="size-full object-cover transition-transform duration-feedback motion-safe:group-hover:scale-[1.02]" />
        ) : (
          <span role="img" aria-label="活动封面占位图" className="flex size-full items-center justify-center bg-[#E9EEF1] text-campus-green"><Image aria-hidden="true" className="size-9" /></span>
        )}
        {favoriteEnabled && <button
          type="button"
          aria-label={`${favorite ? '取消收藏' : '收藏'}${activity.title}`}
          title={favorite ? '取消收藏' : '收藏'}
          disabled={favoritePending}
          onClick={() => onFavorite(activity.id, !favorite)}
          className="absolute right-2.5 top-2.5 z-10 inline-flex size-10 items-center justify-center rounded-full border border-white/80 bg-paper/95 text-primary-700 shadow-panel transition-colors duration-feedback hover:bg-primary-50"
        >
          <Heart aria-hidden="true" className="size-[18px]" fill={favorite ? 'currentColor' : 'none'} />
        </button>}
        <span className="absolute bottom-2.5 left-2.5 rounded-full bg-[#18362E]/90 px-2.5 py-1 text-xs font-semibold text-white">{capacityLabel(activity)}</span>
      </div>

      <div className="flex min-h-0 flex-1 flex-col p-4">
        <div className="flex h-6 items-center gap-2 overflow-hidden">
          {tags.map((tag) => <span key={tag.tag_id} className="truncate rounded-full bg-[#EEF2F3] px-2 py-0.5 text-xs font-medium text-ink-muted">{tag.canonical_name}</span>)}
        </div>
        <h2 className="mt-2 line-clamp-2 h-12 text-base font-bold leading-6 text-ink">{activity.title}</h2>
        <div className="mt-2 flex h-10 min-w-0 items-start gap-1.5 overflow-hidden text-xs font-semibold leading-5 text-primary-700">
          <CalendarDays aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
          <span className="min-w-0">
            <span className="block truncate">{formatDate(activity.activity_start_at)}</span>
            <span className="block truncate text-ink-muted">{formatDeadline(activity.registration_deadline)}</span>
          </span>
        </div>
        <p className="mt-1 h-5 truncate text-sm text-ink-muted">{activity.organizer}</p>
        <div className="mt-2 flex h-5 items-center gap-3 overflow-hidden text-xs text-ink-muted">
          <span className="flex min-w-0 items-center gap-1"><MapPin aria-hidden="true" className="size-3.5 shrink-0" /><span className="truncate">{activity.campus_scope || activity.location_name || '地点待公布'}</span></span>
          <span className="flex shrink-0 items-center gap-1"><UsersRound aria-hidden="true" className="size-3.5" />{activity.participant_count} 人参加</span>
        </div>
        <div className="mt-auto border-t border-stone pt-3">
          <Link to={`/topics/${activity.id}`} aria-label="查看活动详情" className="inline-flex min-h-9 items-center text-sm font-semibold text-primary-700 transition-colors duration-feedback after:absolute after:inset-0 after:content-[''] hover:text-primary-800">查看活动详情</Link>
        </div>
      </div>
    </article>
  )
}
