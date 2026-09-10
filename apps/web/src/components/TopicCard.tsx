import {
  ArrowRight,
  BadgeCheck,
  Bookmark,
  Building2,
  Landmark,
  UsersRound,
} from 'lucide-react'
import { Link } from 'react-router-dom'

import type { Topic } from '@shared/types'

const fallbackCover = '/campus-clocktower-badge.jpg'

export default function TopicCard({ topic }: { topic: Topic }) {
  const SourceIcon = topic.channel === 'official' ? Landmark : BadgeCheck

  return (
    <Link
      to={`/topics/${topic.id}`}
      className="group flex h-full min-w-0 flex-col overflow-hidden rounded-card border border-stone bg-paper shadow-panel transition duration-feedback hover:border-primary-300 hover:shadow-md"
    >
      <div className="relative aspect-[16/7] min-h-32 overflow-hidden border-b border-stone bg-primary-50 sm:aspect-[16/8]">
        <img
          src={topic.cover_url || fallbackCover}
          alt={topic.cover_url ? `${topic.title}活动封面` : ''}
          className="h-full w-full object-cover transition duration-page group-hover:scale-[1.02]"
          loading="lazy"
          onError={(event) => {
            event.currentTarget.onerror = null
            event.currentTarget.src = fallbackCover
            event.currentTarget.alt = ''
          }}
        />
        <span className="absolute left-3 top-3 inline-flex min-h-7 items-center gap-1.5 rounded-card border border-white/70 bg-paper/95 px-2.5 py-1 text-xs font-semibold text-ink shadow-panel">
          <SourceIcon aria-hidden="true" className="size-3.5 text-campus-green" />
          {topic.channel === 'official' ? '官方收录' : '认证组织'}
        </span>
      </div>

      <div className="flex flex-1 flex-col p-4 sm:p-5">
        <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 text-xs text-ink-muted">
          <span className="font-medium text-primary-700">{topic.edition}</span>
          <span className="inline-flex items-center gap-1">
            <Bookmark aria-hidden="true" className="size-3.5" />
            {topic.follower_count} 人关注
          </span>
        </div>

        <h2 className="mt-2 text-lg font-semibold leading-7 text-ink transition-colors group-hover:text-primary-700">
          {topic.title}
        </h2>
        <p className="mt-2 line-clamp-3 text-sm leading-6 text-ink-muted">
          {topic.summary}
        </p>

        <div className="mt-4 flex items-start gap-2 border-t border-stone pt-3 text-xs text-ink-muted">
          <Building2 aria-hidden="true" className="mt-0.5 size-3.5 shrink-0 text-campus-green" />
          <span className="min-w-0">主办方：{topic.organizer}</span>
        </div>

        <div className="mt-auto flex items-center justify-between gap-3 pt-4 text-sm font-semibold text-primary-700">
          <span className="inline-flex items-center gap-1.5">
            <UsersRound aria-hidden="true" className="size-4" />
            查看组队
          </span>
          <ArrowRight aria-hidden="true" className="size-4 transition-transform duration-fast group-hover:translate-x-0.5" />
        </div>
      </div>
    </Link>
  )
}
