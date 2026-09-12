import { CalendarDays, Heart, Image, UsersRound } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { RecommendedHomeTopic } from '@shared/types'

function formatCalendarDate(value: string | null) {
  if (!value) return '时间待公布'

  return new Intl.DateTimeFormat('zh-CN', {
    month: 'long',
    day: 'numeric',
    weekday: 'short',
  }).format(new Date(value))
}

function eventTiming(topic: RecommendedHomeTopic) {
  const activity = formatCalendarDate(topic.activity_start_at)
  if (!topic.registration_deadline) return activity

  return `${activity} · ${formatCalendarDate(topic.registration_deadline)} 截止`
}

export default function HomeEventCard({ topic }: { topic: RecommendedHomeTopic }) {
  const timing = eventTiming(topic)

  return (
    <Link
      to={`/topics/${topic.id}`}
      className="group flex h-[392px] w-[272px] shrink-0 flex-col overflow-hidden rounded-card border border-stone bg-paper shadow-panel transition duration-feedback motion-safe:hover:-translate-y-0.5 hover:border-primary-300 hover:shadow-md"
    >
      <span className="relative block aspect-[16/9] w-full shrink-0 overflow-hidden rounded-t-[12px] bg-[#F1F3F6]">
        {topic.cover_url ? (
          <img
            src={topic.cover_url}
            alt=""
            className="size-full object-cover transition-transform duration-feedback group-hover:scale-[1.02]"
          />
        ) : (
          <span className="flex size-full items-center justify-center text-primary-500">
            <Image aria-hidden="true" className="size-8" />
          </span>
        )}
        <span
          role="img"
          aria-label={topic.followed ? '已收藏' : '未收藏'}
          title={topic.followed ? '已收藏' : '未收藏'}
          className="absolute right-2.5 top-2.5 flex size-9 items-center justify-center rounded-full bg-paper/95 text-primary-700 shadow-panel"
        >
          <Heart aria-hidden="true" className="size-[18px]" fill={topic.followed ? 'currentColor' : 'none'} />
        </span>
      </span>

      <span className="block h-[238px] shrink-0 p-4">
        <span className="line-clamp-2 h-12 text-base font-semibold leading-6 text-ink transition-colors duration-feedback group-hover:text-primary-700">
          {topic.title}
        </span>
        <span className="mt-2 flex h-10 min-w-0 items-start gap-1.5 overflow-hidden text-xs font-semibold leading-5 text-primary-700">
          <CalendarDays aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
          <span aria-label={timing} title={timing} className="line-clamp-2 min-w-0 flex-1">
            {timing}
          </span>
        </span>
        <span className="mt-2 block h-5 truncate text-sm text-ink-muted">{topic.organizer}</span>
        <span className="mt-2 flex h-4 items-center gap-1.5 text-xs text-ink-muted">
          <UsersRound aria-hidden="true" className="size-4" />
          {topic.follower_count} 人关注
        </span>
        <span className="mt-3 block h-[45px] border-t border-stone pt-3 text-xs font-medium leading-4 text-primary-700 line-clamp-2">
          {topic.recommendation_reason}
        </span>
      </span>
    </Link>
  )
}
