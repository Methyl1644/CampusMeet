import { Outlet, Navigate, useLocation } from 'react-router-dom'
import Navbar from '@/components/Navbar'
import { HomeFeedProvider, useHomeFeed } from '@/features/home/HomeFeedContext'
import { requiredRoute } from '@/router/authRouting'
import { useAuthStore } from '@/store/authStore'

function AuthenticatedShell() {
  const { feed, loading, error, reload } = useHomeFeed()
  const unreadState = feed
    ? feed.warnings.includes('unread')
      ? 'degraded'
      : 'ready'
    : error
      ? 'degraded'
      : loading
        ? 'loading'
        : 'degraded'

  return (
    <div className="min-h-dvh bg-[#F8F8FA] text-ink">
      <Navbar
        unread={feed?.unread}
        unreadState={unreadState}
        onRefreshHome={() => void reload()}
        onRetryUnread={() => void reload()}
      />
      <main className="mx-auto w-full max-w-content px-4 pb-[calc(5rem+env(safe-area-inset-bottom))] pt-6 sm:px-6 md:pb-10 md:pt-8 lg:px-8">
        <Outlet />
      </main>
    </div>
  )
}

export default function MainLayout() {
  const location = useLocation()
  const { isAuthenticated, user } = useAuthStore()

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />
  }

  const redirectTo = requiredRoute(user, location.pathname)
  if (redirectTo) {
    return <Navigate to={redirectTo} replace />
  }

  return (
    <HomeFeedProvider>
      <AuthenticatedShell />
    </HomeFeedProvider>
  )
}
