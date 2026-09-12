import { Compass, Home, MessageCircle, Plus } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import type { HomeFeed, User } from '@shared/types'
import UnreadBadge, { unreadLabel } from './UnreadBadge'
import UserMenu from './UserMenu'

const mobileItems = [
  { to: '/home', label: '首页', icon: Home, primary: false },
  { to: '/discover', label: '探索', icon: Compass, primary: false },
  { to: '/publish', label: '发布', icon: Plus, primary: true },
  { to: '/messages', label: '消息', icon: MessageCircle, primary: false },
]

interface MobileNavigationProps {
  unread: HomeFeed['unread']
  user: User
}

export default function MobileNavigation({ unread, user }: MobileNavigationProps) {
  return (
    <nav
      aria-label="移动端主导航"
      className="fixed inset-x-0 bottom-0 z-40 border-t border-stone bg-paper/95 pb-[env(safe-area-inset-bottom)] backdrop-blur md:hidden"
    >
      <div className="grid h-16 grid-cols-5">
        {mobileItems.map(({ to, label, icon: Icon, primary }) => (
          <NavLink
            key={to}
            to={to}
            aria-label={to === '/messages' ? unreadLabel(label, unread.messages) : undefined}
            data-primary-action={primary ? 'true' : undefined}
            className={({ isActive }) =>
              `flex min-w-0 flex-col items-center justify-center gap-0.5 text-[11px] font-medium transition-colors duration-fast ${
                isActive ? 'text-primary-700' : primary ? 'text-primary-600' : 'text-ink-muted'
              }`
            }
          >
            <span
              className={`relative flex shrink-0 items-center justify-center ${
                primary ? 'size-9 rounded-card bg-primary-600 text-white shadow-panel' : 'size-7'
              }`}
            >
              <Icon aria-hidden="true" className="size-5" />
              {to === '/messages' && <UnreadBadge count={unread.messages} />}
            </span>
            <span className="w-full truncate px-1 text-center">{label}</span>
          </NavLink>
        ))}
        <UserMenu user={user} variant="mobile" />
      </div>
    </nav>
  )
}
