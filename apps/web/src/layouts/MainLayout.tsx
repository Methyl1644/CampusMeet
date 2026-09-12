import { Outlet, Navigate } from 'react-router-dom'
import Navbar from '@/components/Navbar'
import { useAuthStore } from '@/store/authStore'

export default function MainLayout() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return (
    <div className="min-h-dvh bg-paper-warm text-ink">
      <Navbar />
      <main className="mx-auto w-full max-w-content px-4 pb-[calc(5.5rem+env(safe-area-inset-bottom))] pt-6 sm:px-6 md:pb-10 md:pt-8 lg:px-8">
        <Outlet />
      </main>
    </div>
  )
}
