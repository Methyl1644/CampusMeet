import { NavLink, useNavigate } from 'react-router-dom'
import { Home, Compass, Plus, MessageCircle, User, LogOut } from 'lucide-react'
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
      {/* 桌面端：顶部导航 */}
      <header className="sticky top-0 z-40 hidden border-b border-gray-200 bg-white md:block">
        <div className="mx-auto flex max-w-content items-center justify-between px-4 py-3">
          <div className="flex items-center gap-8">
            <NavLink to="/home" className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-600 text-white font-bold">
                C
              </div>
              <span className="text-lg font-bold text-gray-900">CampusMate</span>
            </NavLink>
            <nav className="flex items-center gap-6">
              {navItems.map(({ to, label, icon: Icon, isPublish }) => (
                <NavLink
                  key={to}
                  to={to}
                  className={({ isActive }) =>
                    `nav-link ${isActive ? 'nav-link-active' : ''} ${
                      isPublish ? 'text-primary-600 font-semibold' : ''
                    }`
                  }
                >
                  <Icon size={18} />
                  {label}
                </NavLink>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-3">
            {user && (
              <span className="text-sm text-gray-600">{user.nickname}</span>
            )}
            <button
              onClick={handleLogout}
              className="flex items-center gap-1 text-sm text-gray-500 hover:text-red-500"
            >
              <LogOut size={16} />
              退出
            </button>
          </div>
        </div>
      </header>

      {/* 手机端：底部导航 */}
      <nav className="fixed bottom-0 left-0 right-0 z-40 flex border-t border-gray-200 bg-white md:hidden">
        {navItems.map(({ to, label, icon: Icon, isPublish }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex flex-1 flex-col items-center gap-0.5 py-2 text-xs transition-colors ${
                isActive
                  ? 'text-primary-600'
                  : isPublish
                    ? 'text-primary-600'
                    : 'text-gray-500'
              }`
            }
          >
            <div
              className={`flex h-7 w-7 items-center justify-center rounded-full ${
                isPublish ? 'bg-primary-600 text-white' : ''
              }`}
            >
              <Icon size={isPublish ? 20 : 20} />
            </div>
            {label}
          </NavLink>
        ))}
      </nav>
    </>
  )
}
