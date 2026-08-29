import { Outlet, Navigate } from 'react-router-dom'
import Navbar from '@/components/Navbar'
import { useAuthStore } from '@/store/authStore'

export default function MainLayout() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 桌面端顶部导航 */}
      <Navbar />
      {/* 页面内容 */}
      <main className="mx-auto max-w-content px-4 py-4 pb-20 md:pb-4">
        <Outlet />
      </main>
    </div>
  )
}
