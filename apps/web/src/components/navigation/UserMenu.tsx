import {
  Bell,
  CalendarDays,
  ChevronDown,
  CircleHelp,
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
  variant?: 'desktop' | 'mobile'
}

const profileLinks = [
  { to: '/my/activities', label: '我的活动', icon: CalendarDays },
  { to: '/my/groups', label: '我的小组', icon: UsersRound },
  { to: '/users/me', label: '查看个人主页', icon: UserRound },
  { to: '/settings', label: '设置', icon: Settings },
]

const mobileLinks = [
  { to: '/notifications', label: '通知', icon: Bell },
  { to: '/tutorial', label: '教程', icon: CircleHelp },
  ...profileLinks,
]

export default function UserMenu({ user, variant = 'desktop' }: UserMenuProps) {
  const [open, setOpen] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()
  const logout = useAuthStore((state) => state.logout)
  const containerRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const itemRefs = useRef<Array<HTMLAnchorElement | HTMLButtonElement | null>>([])
  const focusItemRef = useRef<number | null>(null)
  const menuLinks = variant === 'mobile' ? mobileLinks : profileLinks

  const closeMenu = () => setOpen(false)

  const closeAndRestoreFocus = () => {
    setOpen(false)
    triggerRef.current?.focus()
  }

  const openFromKeyboard = (index: number) => {
    focusItemRef.current = index
    setOpen(true)
  }

  useEffect(() => {
    if (open && focusItemRef.current !== null) {
      const index = focusItemRef.current
      focusItemRef.current = null
      itemRefs.current[index]?.focus()
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
    if (event.key === 'Tab' && open) {
      closeMenu()
    } else if (event.key === 'ArrowDown' || event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      if (open) {
        itemRefs.current[0]?.focus()
      } else {
        openFromKeyboard(0)
      }
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      const lastIndex = menuLinks.length
      if (open) {
        itemRefs.current[lastIndex]?.focus()
      } else {
        openFromKeyboard(lastIndex)
      }
    }
  }

  const handleMenuKeyDown = (
    event: ReactKeyboardEvent<HTMLAnchorElement | HTMLButtonElement>,
    index: number,
  ) => {
    if (event.key === 'Tab') {
      closeMenu()
      return
    }

    if (event.key === ' ' && event.currentTarget instanceof HTMLAnchorElement) {
      event.preventDefault()
      closeMenu()
      navigate(menuLinks[index].to)
      return
    }

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
    <div ref={containerRef} className={variant === 'mobile' ? 'relative min-w-0' : 'relative ml-1'}>
      <button
        ref={triggerRef}
        type="button"
        aria-label={variant === 'mobile' ? '打开我的菜单' : '打开个人菜单'}
        aria-haspopup="menu"
        aria-expanded={open}
        title={variant === 'mobile' ? '我的' : '个人菜单'}
        onClick={() => setOpen((current) => !current)}
        onKeyDown={handleTriggerKeyDown}
        className={
          variant === 'mobile'
            ? 'flex h-16 w-full min-w-0 flex-col items-center justify-center gap-0.5 text-[11px] font-medium text-ink-muted transition-colors duration-fast hover:text-primary-700'
            : 'flex h-11 items-center gap-1 rounded-card px-1.5 text-ink-muted transition duration-fast hover:bg-primary-50 hover:text-primary-700'
        }
      >
        {variant === 'mobile' ? (
          <>
            <span className="flex size-7 shrink-0 items-center justify-center">
              <UserRound aria-hidden="true" className="size-5" />
            </span>
            <span className="w-full truncate px-1 text-center">我的</span>
          </>
        ) : (
          <>
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
          </>
        )}
      </button>

      {open && (
        <div
          role="menu"
          aria-label={variant === 'mobile' ? '我的菜单' : '个人菜单'}
          className={`absolute right-0 w-52 overflow-y-auto rounded-card border border-stone bg-paper py-1.5 shadow-lg ${
            variant === 'mobile'
              ? 'bottom-[calc(100%+0.5rem)] max-h-[calc(100dvh-6rem-env(safe-area-inset-bottom))]'
              : 'top-[calc(100%+0.5rem)]'
          }`}
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
