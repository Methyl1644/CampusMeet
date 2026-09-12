import { Link } from 'react-router-dom'
import { ArrowRight, CalendarClock, Target, UsersRound } from 'lucide-react'
import type { Post } from '@shared/types'
import SourceBadge from './SourceBadge'
import RiskTag from './RiskTag'
import StatusBadge from './StatusBadge'

export default function PostCard({ post }: { post: Post }) {
  return (
    <Link
      to={`/posts/${post.id}`}
      className="group flex h-full min-w-0 flex-col rounded-card border border-stone bg-paper p-4 shadow-panel transition duration-feedback hover:border-primary-300 hover:shadow-md"
    >
      <div className="flex flex-wrap items-center gap-2">
        <SourceBadge type={post.source_type} />
        <span className="text-xs text-ink-muted">{post.main_category}</span>
        <span className="ml-auto">
          <StatusBadge status={post.status} />
        </span>
        {post.risk_level !== 'low' && <RiskTag level={post.risk_level} />}
      </div>

      <h3 className="mt-3 line-clamp-2 text-base font-semibold leading-6 text-ink transition-colors group-hover:text-primary-700">
        {post.title}
      </h3>

      <div className="mt-3 grid gap-2 text-xs text-ink-muted">
        <span className="flex min-w-0 items-start gap-2">
          <Target aria-hidden="true" className="mt-0.5 size-3.5 shrink-0 text-campus-green" />
          <span className="min-w-0">
            活动：<span className="font-medium text-ink">{post.activity_name}</span>
          </span>
        </span>
        {post.needed_roles.length > 0 && (
          <span className="flex min-w-0 items-start gap-2">
            <UsersRound aria-hidden="true" className="mt-0.5 size-3.5 shrink-0 text-campus-green" />
            <span className="min-w-0">缺少：{post.needed_roles.join(' ')}</span>
          </span>
        )}
        <span className="flex items-start gap-2">
          <CalendarClock aria-hidden="true" className="mt-0.5 size-3.5 shrink-0 text-campus-green" />
          <span>截止 {post.deadline}</span>
        </span>
      </div>

      <div className="mt-auto flex min-h-9 items-end justify-between gap-3 border-t border-stone pt-3">
        {post.match_score !== undefined ? (
          <span className="text-sm font-semibold text-primary-700">
            匹配度 {post.match_score}%
          </span>
        ) : (
          <span className="text-xs font-medium text-ink-muted">
            {post.current_members}/{post.target_members} 人
          </span>
        )}
        {post.status === 'recruiting' && (
          <span className="inline-flex items-center gap-1 text-sm font-semibold text-primary-700">
            申请<ArrowRight aria-hidden="true" className="size-4 transition-transform duration-fast group-hover:translate-x-0.5" />
          </span>
        )}
      </div>
    </Link>
  )
}
