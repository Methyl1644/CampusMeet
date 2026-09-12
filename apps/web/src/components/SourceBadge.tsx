import { SOURCE_BADGE } from '@shared/constants'
import type { SourceType } from '@shared/types'
import { BadgeCheck, Landmark, UserRound } from 'lucide-react'

const sourceStyles = {
  official: {
    icon: Landmark,
    className: 'border-campus-gold/30 bg-amber-50 text-amber-800',
  },
  organization: {
    icon: BadgeCheck,
    className: 'border-campus-green/25 bg-green-50 text-campus-green',
  },
  user: {
    icon: UserRound,
    className: 'border-stone bg-paper-warm text-ink-muted',
  },
} satisfies Record<
  SourceType,
  { icon: typeof Landmark; className: string }
>

export default function SourceBadge({ type }: { type: SourceType }) {
  const config = SOURCE_BADGE[type]
  const style = sourceStyles[type]
  const Icon = style.icon

  return (
    <span
      aria-label={`来源：${config.label}`}
      className={`inline-flex min-h-6 items-center gap-1 whitespace-nowrap rounded-card border px-2 py-0.5 text-xs font-medium ${style.className}`}
    >
      <Icon aria-hidden="true" className="size-3.5 shrink-0" />
      {config.label}
    </span>
  )
}
