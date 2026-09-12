import { useState } from 'react'
import { ArrowRight, Clock3, X } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { HomeDeadlineReminder } from '@shared/types'

export default function DeadlineReminder({
  reminder,
}: {
  reminder: HomeDeadlineReminder | null
}) {
  const [dismissed, setDismissed] = useState(false)

  if (!reminder || dismissed) return null

  return (
    <aside
      role="status"
      aria-live="polite"
      className="relative flex min-w-0 items-start gap-3 rounded-card border border-primary-200 bg-primary-50 px-4 py-3 pr-12 text-ink"
    >
      <span className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-card bg-paper text-primary-700 shadow-panel">
        <Clock3 aria-hidden="true" className="size-[18px]" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-xs font-semibold text-primary-700">
          距报名截止还有 {reminder.days_remaining} 天
        </p>
        <p className="mt-0.5 line-clamp-2 text-sm font-semibold leading-5 text-ink">
          {reminder.title}
        </p>
        <Link
          to={`/topics/${reminder.id}`}
          className="mt-1.5 inline-flex items-center gap-1 text-sm font-semibold text-primary-700 transition-colors duration-fast hover:text-primary-800"
        >
          查看活动
          <ArrowRight aria-hidden="true" className="size-3.5" />
        </Link>
      </div>
      <button
        type="button"
        aria-label="关闭截止提醒"
        title="关闭截止提醒"
        onClick={() => setDismissed(true)}
        className="absolute right-2 top-2 flex size-9 items-center justify-center rounded-card text-ink-muted transition-colors duration-fast hover:bg-primary-100 hover:text-primary-700"
      >
        <X aria-hidden="true" className="size-[18px]" />
      </button>
    </aside>
  )
}
