import { ArrowRight, UsersRound } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { HomeJoinedGroup } from '@shared/types'

export default function MyGroupsSummary({ groups }: { groups: HomeJoinedGroup[] }) {
  const group = groups[0]

  return (
    <section aria-labelledby="home-groups-title" className="rounded-card border border-stone bg-paper p-4 shadow-panel">
      <div className="flex items-center justify-between gap-3">
        <h2 id="home-groups-title" className="text-base font-semibold text-ink">
          我的小组
        </h2>
        <Link
          to="/my/groups"
          className="inline-flex items-center gap-1 text-xs font-semibold text-primary-700 transition-colors duration-fast hover:text-primary-800"
        >
          查看全部小组
          <ArrowRight aria-hidden="true" className="size-3.5" />
        </Link>
      </div>

      <div className="mt-3 flex min-h-[72px] items-center border-t border-stone pt-3">
        {group ? (
          <Link
            to={`/teams/${group.id}`}
            aria-label={group.activity_name}
            className="group flex min-w-0 flex-1 items-center gap-3"
          >
            <span className="flex size-11 shrink-0 items-center justify-center rounded-card bg-[#F3F2F6] text-primary-600">
              <UsersRound aria-hidden="true" className="size-5" />
            </span>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-semibold text-ink transition-colors duration-fast group-hover:text-primary-700">
                {group.activity_name}
              </span>
              <span className="mt-1 block text-xs text-ink-muted">
                <span>{`${group.current_members} / ${group.target_members} 人`}</span>
                <span aria-hidden="true"> · </span>
                {group.member_role === 'owner' ? '我创建的' : '已加入'}
              </span>
            </span>
          </Link>
        ) : (
          <div className="flex min-w-0 flex-1 items-center justify-between gap-3">
            <p className="text-sm text-ink-muted">还没有加入小组</p>
            <Link
              to="/discover?view=group"
              className="shrink-0 text-sm font-semibold text-primary-700 hover:text-primary-800"
            >
              探索小组
            </Link>
          </div>
        )}
      </div>
    </section>
  )
}
