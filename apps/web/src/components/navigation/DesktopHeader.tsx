import { Bell, CircleHelp, Compass, Home, MessageCircle, Plus, RefreshCw } from 'lucide-react'
import { NavLink, useLocation } from 'react-router-dom'
import type { HomeFeed, User } from '@shared/types'
import CampusMark from '@/components/CampusMark'
import UnreadBadge, { unreadLabel } from './UnreadBadge'
import UserMenu from './UserMenu'

interface DesktopHeaderProps {
  unread: HomeFeed['unread']
  unreadState: 'loading' | 'ready' | 'degraded'
  user: User
  onRefreshHome?: () => void
  onRetryUnread?: () => void
}

const primaryItems = [
  { to: '/home', label: '首页', icon: Home },
  { to: '/discover', label: '探索', icon: Compass },
  { to: '/publish', label: '发布', icon: Plus },
]

function navUnreadLabel(label: string, count: number, state: DesktopHeaderProps['unreadState']) {
  if (state === 'loading') return `${label}，未读数加载中`
  if (state === 'degraded') return `${label}，未读数暂不可用`
  return unreadLabel(label, count)
}

export default function DesktopHeader({
  unread,
  unreadState,
  user,
  onRefreshHome,
  onRetryUnread,
}: DesktopHeaderProps) {
  const location = useLocation()

  return (
    <header
      aria-label="桌面端应用导航"
      className="sticky top-0 z-40 hidden h-[72px] border-b border-stone bg-paper/95 backdrop-blur md:block"
    >
      <div className="mx-auto flex h-[72px] max-w-content items-center px-4 lg:px-8">
        <NavLink to="/home" aria-label="CampusMate 首页" className="mr-5 shrink-0 lg:mr-8">
          <span className="lg:hidden">
            <CampusMark compact />
          </span>
          <span className="hidden lg:inline-flex">
            <CampusMark />
          </span>
        </NavLink>

        <nav aria-label="桌面端主导航" className="flex h-[72px] items-stretch gap-3 lg:gap-6">
          {primaryItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              onClick={() => {
                if (to === '/home' && location.pathname === '/home') onRefreshHome?.()
              }}
              className={({ isActive }) =>
                `nav-link h-[72px] whitespace-nowrap pt-0 ${isActive ? 'nav-link-active' : ''}`
              }
            >
              <Icon aria-hidden="true" className="size-[18px] shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="flex-1" />

        <div className="flex h-full shrink-0 items-center gap-1 lg:gap-2">
          <NavLink
            to="/messages"
            aria-label={navUnreadLabel('消息', unread.messages, unreadState)}
            title="消息"
            className={({ isActive }) =>
              `relative flex size-10 items-center justify-center rounded-card transition duration-fast hover:bg-primary-50 hover:text-primary-700 ${
                isActive ? 'text-primary-700' : 'text-ink-muted'
              }`
            }
          >
            <MessageCircle aria-hidden="true" className="size-5" />
            {unreadState === 'ready' && <UnreadBadge count={unread.messages} />}
          </NavLink>
          <NavLink
            to="/notifications"
            aria-label={navUnreadLabel('通知', unread.notifications, unreadState)}
            title="通知"
            className="relative flex size-10 items-center justify-center rounded-card text-ink-muted transition duration-fast hover:bg-primary-50 hover:text-primary-700"
          >
            <Bell aria-hidden="true" className="size-5" />
            {unreadState === 'ready' && <UnreadBadge count={unread.notifications} />}
          </NavLink>
          {unreadState === 'degraded' && (
            <button
              type="button"
              aria-label="重新加载未读数"
              title="重新加载未读数"
              onClick={onRetryUnread}
              className="flex size-10 items-center justify-center rounded-card text-ink-muted transition duration-fast hover:bg-primary-50 hover:text-primary-700"
            >
              <RefreshCw aria-hidden="true" className="size-4" />
            </button>
          )}
          <NavLink
            to="/tutorial"
            aria-label="教程"
            title="教程"
            className={({ isActive }) =>
              `flex size-10 items-center justify-center rounded-card transition duration-fast hover:bg-primary-50 hover:text-primary-700 ${
                isActive ? 'text-primary-700' : 'text-ink-muted'
              }`
            }
          >
            <CircleHelp aria-hidden="true" className="size-5" />
          </NavLink>
          <UserMenu user={user} />
        </div>
      </div>
    </header>
  )
}
