import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'
import { CheckCircle, XCircle, Info, X } from 'lucide-react'

type ToastType = 'success' | 'error' | 'info'

interface ToastItem {
  id: number
  type: ToastType
  message: string
}

interface ToastContextValue {
  showToast: (message: string, type?: ToastType) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

let toastId = 0

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([])

  const showToast = useCallback((message: string, type: ToastType = 'info') => {
    const id = ++toastId
    setToasts((prev) => [...prev, { id, type, message }])

    const duration = type === 'error' ? 0 : type === 'success' ? 2000 : 3000
    if (duration > 0) {
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id))
      }, duration)
    }
  }, [])

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      {/* Toast 容器 */}
      <div className="fixed right-4 top-4 z-50 flex flex-col gap-2">
        {toasts.map((toast) => {
          const config = {
            success: { icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-50 border-green-200' },
            error: { icon: XCircle, color: 'text-red-500', bg: 'bg-red-50 border-red-200' },
            info: { icon: Info, color: 'text-blue-500', bg: 'bg-blue-50 border-blue-200' },
          }[toast.type]
          const Icon = config.icon
          return (
            <div
              key={toast.id}
              className={`flex items-center gap-2 rounded-lg border px-4 py-2.5 shadow-md ${config.bg} animate-slide-up`}
            >
              <Icon size={18} className={config.color} />
              <span className="text-sm text-gray-700">{toast.message}</span>
              {toast.type === 'error' && (
                <button onClick={() => dismiss(toast.id)} className="ml-2 text-gray-400 hover:text-gray-600">
                  <X size={14} />
                </button>
              )}
            </div>
          )
        })}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within ToastProvider')
  return ctx
}
