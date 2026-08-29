import { createBrowserRouter, Navigate } from 'react-router-dom'
import MainLayout from '@/layouts/MainLayout'
import Login from '@/pages/Login'
import Home from '@/pages/Home'
import Discover from '@/pages/Discover'
import Publish from '@/pages/Publish'
import PostDetail from '@/pages/PostDetail'
import Messages from '@/pages/Messages'
import TeamDetail from '@/pages/TeamDetail'
import Profile from '@/pages/Profile'

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <Login />,
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
      { path: 'messages', element: <Messages /> },
      { path: 'teams/:id', element: <TeamDetail /> },
      { path: 'profile', element: <Profile /> },
    ],
  },
])
