import { Bell, ChevronRight } from 'lucide-react'
import type { Notification } from '@shared/types'

export function notificationTarget(item: Notification): string | null {
  const authorizationTargets = new Set([
    'platform_role_grant',
    'organization_invitation',
    'organization_ownership_transfer',
  ])
  if (
    (item.target_type && authorizationTargets.has(item.target_type))
    || item.event_type.includes('invited')
    || item.event_type.includes('ownership_transfer')
  ) {
    return '/authorizations'
  }
  if (!item.target_id) return null
  const routes: Record<string, string> = {
    topic: `/topics/${item.target_id}`,
    post: `/posts/${item.target_id}`,
    team: `/teams/${item.target_id}`,
    conversation: `/messages/${item.target_id}`,
  }
  return item.target_type ? routes[item.target_type] ?? null : null
}

export default function NotificationItem({ item, onOpen }: { item: Notification; onOpen: (item: Notification) => void }) {
  const target = notificationTarget(item)
  return (
    <button
      type="button"
      onClick={() => onOpen(item)}
      className="flex min-h-24 w-full items-start gap-4 border-b border-stone px-1 py-5 text-left transition-colors hover:bg-paper"
    >
      <span className={`mt-0.5 flex size-10 shrink-0 items-center justify-center rounded-full ${item.read_at ? 'bg-[#ECECEF] text-ink-muted' : 'bg-primary-100 text-primary-700'}`}>
        <Bell aria-hidden="true" className="size-5" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="flex items-center gap-2">
          <span className="font-bold text-ink">{item.title}</span>
          {!item.read_at && <span className="size-2 rounded-full bg-primary-600" aria-label="未读" />}
        </span>
        <span className="mt-1 block text-sm leading-6 text-ink-muted">{item.body}</span>
        <time className="mt-2 block text-xs text-ink-muted">{new Date(item.created_at).toLocaleString('zh-CN')}</time>
      </span>
      {target && <ChevronRight aria-hidden="true" className="mt-2 size-4 shrink-0 text-ink-muted" />}
    </button>
  )
}
