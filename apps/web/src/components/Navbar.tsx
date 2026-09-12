import type { HomeFeed } from '@shared/types'
import DesktopHeader from '@/components/navigation/DesktopHeader'
import MobileNavigation from '@/components/navigation/MobileNavigation'
import { useAuthStore } from '@/store/authStore'

interface NavbarProps {
  unread?: HomeFeed['unread']
  onRefreshHome?: () => void
}

const emptyUnread: HomeFeed['unread'] = { messages: 0, notifications: 0 }

export default function Navbar({ unread = emptyUnread, onRefreshHome }: NavbarProps) {
  const user = useAuthStore((state) => state.user)

  if (!user) return null

  return (
    <>
      <DesktopHeader unread={unread} user={user} onRefreshHome={onRefreshHome} />
      <MobileNavigation unread={unread} user={user} />
    </>
  )
}
