import type { HomeFeed } from '@shared/types'
import DesktopHeader from '@/components/navigation/DesktopHeader'
import MobileNavigation from '@/components/navigation/MobileNavigation'
import { useAuthStore } from '@/store/authStore'

interface NavbarProps {
  unread?: HomeFeed['unread']
  unreadState?: 'loading' | 'ready' | 'degraded'
  onRefreshHome?: () => void
  onRetryUnread?: () => void
}

const emptyUnread: HomeFeed['unread'] = { messages: 0, notifications: 0 }

export default function Navbar({
  unread = emptyUnread,
  unreadState = 'ready',
  onRefreshHome,
  onRetryUnread,
}: NavbarProps) {
  const user = useAuthStore((state) => state.user)

  if (!user) return null

  return (
    <>
      <DesktopHeader
        unread={unread}
        unreadState={unreadState}
        user={user}
        onRefreshHome={onRefreshHome}
        onRetryUnread={onRetryUnread}
      />
      <MobileNavigation
        unread={unread}
        unreadState={unreadState}
        user={user}
        onRetryUnread={onRetryUnread}
      />
    </>
  )
}
