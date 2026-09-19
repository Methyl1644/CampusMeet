import { lazy, Suspense, type ReactNode } from 'react'
import { createBrowserRouter, Navigate, type RouteObject } from 'react-router-dom'
import MainLayout from '@/layouts/MainLayout'
import Login from '@/pages/Login'
import { successfulAuthNavigation } from '@/pages/authFlow'
import RouteError from '@/pages/RouteError'
import { useAuthStore } from '@/store/authStore'

const Onboarding = lazy(() => import('@/pages/Onboarding'))
const Home = lazy(() => import('@/pages/Home'))
const Discover = lazy(() => import('@/pages/Discover'))
const Publish = lazy(() => import('@/pages/Publish'))
const PublishActivity = lazy(() => import('@/pages/PublishActivity'))
const PostDetail = lazy(() => import('@/pages/PostDetail'))
const Messages = lazy(() => import('@/pages/Messages'))
const TeamDetail = lazy(() => import('@/pages/TeamDetail'))
const TopicDetail = lazy(() => import('@/pages/TopicDetail'))
const Tutorial = lazy(() => import('@/pages/Tutorial'))
const MyActivities = lazy(() => import('@/pages/MyActivities'))
const MyGroups = lazy(() => import('@/pages/MyGroups'))
const Notifications = lazy(() => import('@/pages/Notifications'))
const PublicProfile = lazy(() => import('@/pages/PublicProfile'))
const Settings = lazy(() => import('@/pages/Settings'))
const ProfileRedirect = lazy(() => import('@/pages/ProfileRedirect'))
const Management = lazy(() => import('@/pages/Management'))
const Authorizations = lazy(() => import('@/pages/Authorizations'))
const Legal = lazy(() => import('@/pages/Legal'))

function RouteLoading() {
  return (
    <div className="flex min-h-[40vh] items-center justify-center" role="status" aria-live="polite">
      <span className="text-sm text-ink-soft">正在打开页面...</span>
    </div>
  )
}

function deferred(element: ReactNode) {
  return <Suspense fallback={<RouteLoading />}>{element}</Suspense>
}

function LoginRoute() {
  const { isAuthenticated, user } = useAuthStore()

  if (isAuthenticated && user) {
    const navigation = successfulAuthNavigation(user)
    return <Navigate to={navigation.to} replace={navigation.replace} />
  }

  return <Login />
}

export const appRoutes: RouteObject[] = [
  {
    path: '/login',
    element: <LoginRoute />,
  },
  { path: '/terms', element: deferred(<Legal kind="terms" />) },
  { path: '/privacy', element: deferred(<Legal kind="privacy" />) },
  {
    path: '/onboarding',
    element: deferred(<Onboarding />),
  },
  {
    path: '/',
    element: <MainLayout />,
    errorElement: <RouteError />,
    children: [
      { index: true, element: <Navigate to="/home" replace /> },
      { path: 'home', element: deferred(<Home />) },
      { path: 'discover', element: deferred(<Discover />) },
      { path: 'publish', element: deferred(<Publish />) },
      { path: 'publish/activity', element: deferred(<PublishActivity />) },
      { path: 'posts/:id', element: deferred(<PostDetail />) },
      { path: 'topics/:id', element: deferred(<TopicDetail />) },
      { path: 'messages', element: deferred(<Messages />) },
      { path: 'messages/:conversationId', element: deferred(<Messages />) },
      { path: 'tutorial', element: deferred(<Tutorial />) },
      { path: 'teams/:id', element: deferred(<TeamDetail />) },
      { path: 'profile', element: deferred(<ProfileRedirect />) },
      { path: 'my/activities', element: deferred(<MyActivities />) },
      { path: 'my/groups', element: deferred(<MyGroups />) },
      { path: 'notifications', element: deferred(<Notifications />) },
      { path: 'users/:id', element: deferred(<PublicProfile />) },
      { path: 'settings', element: deferred(<Settings />) },
      { path: 'management', element: deferred(<Management />) },
      { path: 'authorizations', element: deferred(<Authorizations />) },
      { path: '*', element: <RouteError notFound /> },
    ],
  },
]

export const router = createBrowserRouter(appRoutes)
