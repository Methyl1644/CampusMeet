import { Inbox } from 'lucide-react'
import type { ReactNode } from 'react'
import { Reveal } from '@/components/motion/Reveal'

interface EmptyStateProps {
  title?: string
  description?: string
  action?: ReactNode
}

export default function EmptyState({
  title = '暂无内容',
  description = '',
  action,
}: EmptyStateProps) {
  return (
    <Reveal className="flex min-h-56 flex-col items-center justify-center px-4 py-16 text-center">
      <span className="mb-3 flex size-12 items-center justify-center rounded-card border border-stone bg-paper text-ink-muted">
        <Inbox aria-hidden="true" className="size-6" />
      </span>
      <p className="mb-1 text-sm font-semibold text-ink">{title}</p>
      {description && (
        <p className="mb-4 max-w-md text-xs leading-5 text-ink-muted">
          {description}
        </p>
      )}
      {action}
    </Reveal>
  )
}
