import { Inbox } from 'lucide-react'
import type { ReactNode } from 'react'

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
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <Inbox size={48} className="mb-3 text-gray-300" />
      <p className="mb-1 text-sm font-medium text-gray-600">{title}</p>
      {description && <p className="mb-4 text-xs text-gray-400">{description}</p>}
      {action}
    </div>
  )
}
