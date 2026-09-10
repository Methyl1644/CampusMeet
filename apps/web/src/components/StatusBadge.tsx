import { POST_STATUS } from '@shared/constants'
import type { PostStatus } from '@shared/types'
import { CalendarX2, CircleCheck, LockKeyhole, UsersRound } from 'lucide-react'

const statusStyles = {
  recruiting: {
    icon: CircleCheck,
    className: 'border-campus-green/25 bg-green-50 text-campus-green',
  },
  full: {
    icon: UsersRound,
    className: 'border-stone bg-paper-warm text-ink-muted',
  },
  closed: {
    icon: LockKeyhole,
    className: 'border-stone bg-paper-warm text-ink-muted',
  },
  expired: {
    icon: CalendarX2,
    className: 'border-red-200 bg-red-50 text-red-700',
  },
} satisfies Record<
  PostStatus,
  { icon: typeof CircleCheck; className: string }
>

export default function StatusBadge({ status }: { status: PostStatus }) {
  const config = POST_STATUS[status]
  const style = statusStyles[status]
  const Icon = style.icon

  return (
    <span
      aria-label={`招募状态：${config.label}`}
      className={`inline-flex min-h-6 items-center gap-1 whitespace-nowrap rounded-card border px-2 py-0.5 text-xs font-medium ${style.className}`}
    >
      <Icon aria-hidden="true" className="size-3.5 shrink-0" />
      {config.label}
    </span>
  )
}
