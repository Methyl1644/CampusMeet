import {
  CalendarDays,
  ChevronDown,
  LogOut,
  Settings,
  UserRound,
  UsersRound,
} from 'lucide-react'
import {
  useEffect,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
} from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import type { User } from '@shared/types'
import { useAuthStore } from '@/store/authStore'

interface UserMenuProps {
  user: User
}

const menuLinks = [
  { to: '/profile?tab=events', label: '我的活动', icon: CalendarDays },
  { to: '/profile?tab=groups', label: '我的小组', icon: UsersRound },
  { to: '/profile?view=public', label: '查看个人主页', icon: UserRound },
  { to: '/profile?view=settings', label: '设置', icon: Settings },
]

export default function UserMenu({ user }: UserMenuProps) {
  const [open, setOpen] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()
  const logout = useAuthStore((state) => state.logout)
  const containerRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const itemRefs = useRef<Array<HTMLAnchorElement | HTMLButtonElement | null>>([])
  const focusFirstItemRef = useRef(false)

  const closeMenu = () => setOpen(false)

  const closeAndRestoreFocus = () => {
    setOpen(false)
    triggerRef.current?.focus()
  }

  const openFromKeyboard = () => {
    focusFirstItemRef.current = true
    setOpen(true)
  }

  useEffect(() => {
    if (open && focusFirstItemRef.current) {
      focusFirstItemRef.current = false
      itemRefs.current[0]?.focus()
    }
  }, [open])

  useEffect(() => {
    closeMenu()
  }, [location.pathname, location.search])

  useEffect(() => {
    if (!open) return

    const handleOutsidePointer = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) {
        closeMenu()
      }
    }

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        closeAndRestoreFocus()
      }
    }

    document.addEventListener('mousedown', handleOutsidePointer)
    document.addEventListener('keydown', handleEscape)

    return () => {
      document.removeEventListener('mousedown', handleOutsidePointer)
      document.removeEventListener('keydown', handleEscape)
    }
  }, [open])

  const handleTriggerKeyDown = (event: ReactKeyboardEvent<HTMLButtonElement>) => {
    if (event.key === 'ArrowDown' || event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      if (open) {
        itemRefs.current[0]?.focus()
      } else {
        openFromKeyboard()
      }
    }
  }

  const handleMenuKeyDown = (
    event: ReactKeyboardEvent<HTMLAnchorElement | HTMLButtonElement>,
    index: number,
  ) => {
    if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp') return

    event.preventDefault()
    const direction = event.key === 'ArrowDown' ? 1 : -1
    const nextIndex = (index + direction + itemRefs.current.length) % itemRefs.current.length
    itemRefs.current[nextIndex]?.focus()
  }

  const handleLogout = () => {
    closeMenu()
    logout()
    navigate('/login')
  }

  const avatarFallback = user.nickname.trim().slice(0, 1) || '我'

  return (
    <div ref={containerRef} className="relative ml-1">
      <button
        ref={triggerRef}
        type="button"
        aria-label="打开个人菜单"
        aria-haspopup="menu"
        aria-expanded={open}
        title="个人菜单"
        onClick={() => setOpen((current) => !current)}
        onKeyDown={handleTriggerKeyDown}
        className="flex h-11 items-center gap-1 rounded-card px-1.5 text-ink-muted transition duration-fast hover:bg-primary-50 hover:text-primary-700"
      >
        {user.avatar ? (
          <img
            src={user.avatar}
            alt=""
            className="size-8 rounded-full border border-stone object-cover"
          />
        ) : (
          <span className="flex size-8 items-center justify-center rounded-full bg-primary-100 text-sm font-semibold text-primary-800">
            {avatarFallback}
          </span>
        )}
        <ChevronDown aria-hidden="true" className="size-4" />
      </button>

      {open && (
        <div
          role="menu"
          aria-label="个人菜单"
          className="absolute right-0 top-[calc(100%+0.5rem)] w-52 overflow-hidden rounded-card border border-stone bg-paper py-1.5 shadow-lg"
        >
          {menuLinks.map(({ to, label, icon: Icon }, index) => (
            <Link
              key={to}
              ref={(element) => {
                itemRefs.current[index] = element
              }}
              to={to}
              role="menuitem"
              tabIndex={-1}
              onClick={closeMenu}
              onKeyDown={(event) => handleMenuKeyDown(event, index)}
              className="flex min-h-10 items-center gap-3 px-3 text-sm text-ink transition duration-fast hover:bg-primary-50 hover:text-primary-700 focus-visible:bg-primary-50"
            >
              <Icon aria-hidden="true" className="size-[18px] text-ink-muted" />
              {label}
            </Link>
          ))}
          <div className="my-1 border-t border-stone" />
          <button
            ref={(element) => {
              itemRefs.current[menuLinks.length] = element
            }}
            type="button"
            role="menuitem"
            tabIndex={-1}
            onClick={handleLogout}
            onKeyDown={(event) => handleMenuKeyDown(event, menuLinks.length)}
            className="flex min-h-10 w-full items-center gap-3 px-3 text-left text-sm text-red-700 transition duration-fast hover:bg-red-50 focus-visible:bg-red-50"
          >
            <LogOut aria-hidden="true" className="size-[18px]" />
            退出登录
          </button>
        </div>
      )}
    </div>
  )
}
