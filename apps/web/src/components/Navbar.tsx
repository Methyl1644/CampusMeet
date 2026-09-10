import { NavLink, useNavigate } from 'react-router-dom'
import { Home, Compass, Plus, MessageCircle, User, LogOut } from 'lucide-react'
import CampusMark from '@/components/CampusMark'
import { useAuthStore } from '@/store/authStore'

const navItems = [
  { to: '/home', label: '首页', icon: Home },
  { to: '/discover', label: '发现', icon: Compass },
  { to: '/publish', label: '发布', icon: Plus, isPublish: true },
  { to: '/messages', label: '消息', icon: MessageCircle },
  { to: '/profile', label: '我的', icon: User },
]

export default function Navbar() {
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <>
      <header className="sticky top-0 z-40 hidden h-[72px] border-b border-stone bg-paper/95 md:block">
        <div className="mx-auto flex h-[72px] max-w-content items-center gap-8 px-6 lg:px-8">
          <div className="flex min-w-0 flex-1 items-center gap-8">
            <NavLink
              to="/home"
              aria-label="CampusMate 首页"
              className="shrink-0"
            >
              <CampusMark />
            </NavLink>
            <nav aria-label="主导航" className="flex h-[72px] items-stretch gap-6">
              {navItems.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  className={({ isActive }) =>
                    `nav-link h-[72px] whitespace-nowrap pt-0 ${isActive ? 'nav-link-active' : ''}`
                  }
                >
                  <Icon aria-hidden="true" className="size-[18px] shrink-0" />
                  {label}
                </NavLink>
              ))}
            </nav>
          </div>
          <div className="flex shrink-0 items-center gap-3 border-l border-stone pl-5">
            {user && (
              <span className="max-w-32 truncate text-sm text-ink-muted">
                {user.nickname}
              </span>
            )}
            <button
              type="button"
              aria-label="退出登录"
              title="退出登录"
              onClick={handleLogout}
              className="icon-button size-9 hover:bg-red-50 hover:text-red-700"
            >
              <LogOut aria-hidden="true" className="size-[18px]" />
            </button>
          </div>
        </div>
      </header>

      <nav
        aria-label="移动端主导航"
        className="fixed inset-x-0 bottom-0 z-40 border-t border-stone bg-paper/95 md:hidden"
        style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
      >
        <div className="grid h-16 grid-cols-5">
        {navItems.map(({ to, label, icon: Icon, isPublish }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex min-w-0 flex-col items-center justify-center gap-0.5 text-[11px] font-medium transition-colors duration-fast ${
                isActive
                  ? 'text-primary-700'
                  : isPublish
                    ? 'text-primary-600'
                    : 'text-ink-muted'
              }`
            }
          >
            <span
              className={`flex shrink-0 items-center justify-center ${
                isPublish
                  ? 'size-9 rounded-card bg-primary-600 text-white shadow-panel'
                  : 'size-7'
              }`}
            >
              <Icon
                aria-hidden="true"
                className="size-5"
              />
            </span>
            <span className="w-full truncate px-1 text-center">{label}</span>
          </NavLink>
        ))}
        </div>
      </nav>
    </>
  )
}
