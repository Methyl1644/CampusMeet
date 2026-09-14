import { createBrowserRouter, Navigate, type RouteObject } from 'react-router-dom'
import MainLayout from '@/layouts/MainLayout'
import Login from '@/pages/Login'
import Onboarding from '@/pages/Onboarding'
import { successfulAuthNavigation } from '@/pages/authFlow'
import Home from '@/pages/Home'
import Discover from '@/pages/Discover'
import Publish from '@/pages/Publish'
import PostDetail from '@/pages/PostDetail'
import Messages from '@/pages/Messages'
import TeamDetail from '@/pages/TeamDetail'
import TopicDetail from '@/pages/TopicDetail'
import Tutorial from '@/pages/Tutorial'
import MyActivities from '@/pages/MyActivities'
import MyGroups from '@/pages/MyGroups'
import Notifications from '@/pages/Notifications'
import PublicProfile from '@/pages/PublicProfile'
import Settings from '@/pages/Settings'
import ProfileRedirect from '@/pages/ProfileRedirect'
import Management from '@/pages/Management'
import Authorizations from '@/pages/Authorizations'
import { useAuthStore } from '@/store/authStore'

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
  {
    path: '/onboarding',
    element: <Onboarding />,
  },
  {
    path: '/',
    element: <MainLayout />,
    children: [
      { index: true, element: <Navigate to="/home" replace /> },
      { path: 'home', element: <Home /> },
      { path: 'discover', element: <Discover /> },
      { path: 'publish', element: <Publish /> },
      { path: 'posts/:id', element: <PostDetail /> },
      { path: 'topics/:id', element: <TopicDetail /> },
      { path: 'messages', element: <Messages /> },
      { path: 'messages/:conversationId', element: <Messages /> },
      { path: 'tutorial', element: <Tutorial /> },
      { path: 'teams/:id', element: <TeamDetail /> },
      { path: 'profile', element: <ProfileRedirect /> },
      { path: 'my/activities', element: <MyActivities /> },
      { path: 'my/groups', element: <MyGroups /> },
      { path: 'notifications', element: <Notifications /> },
      { path: 'users/:id', element: <PublicProfile /> },
      { path: 'settings', element: <Settings /> },
      { path: 'management', element: <Management /> },
      { path: 'authorizations', element: <Authorizations /> },
    ],
  },
]

export const router = createBrowserRouter(appRoutes)
