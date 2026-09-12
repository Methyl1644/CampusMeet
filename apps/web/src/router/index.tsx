import { createBrowserRouter, Navigate } from 'react-router-dom'
import MainLayout from '@/layouts/MainLayout'
import Login from '@/pages/Login'
import Onboarding from '@/pages/Onboarding'
import Home from '@/pages/Home'
import Discover from '@/pages/Discover'
import Publish from '@/pages/Publish'
import PostDetail from '@/pages/PostDetail'
import Messages from '@/pages/Messages'
import TeamDetail from '@/pages/TeamDetail'
import Profile from '@/pages/Profile'
import TopicDetail from '@/pages/TopicDetail'
import Tutorial from '@/pages/Tutorial'

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <Login />,
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
      { path: 'tutorial', element: <Tutorial /> },
      { path: 'teams/:id', element: <TeamDetail /> },
      { path: 'profile', element: <Profile /> },
    ],
  },
])
