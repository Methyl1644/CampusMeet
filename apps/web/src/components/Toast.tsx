import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'
import { CheckCircle2, CircleAlert, Info, X } from 'lucide-react'

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
    setToasts((prev) => (
      prev.some((toast) => toast.type === type && toast.message === message)
        ? prev
        : [...prev, { id, type, message }]
    ))

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
      <div
        className="pointer-events-none fixed inset-x-4 top-4 z-50 flex flex-col items-end gap-2 sm:left-auto sm:w-96"
      >
        {toasts.map((toast) => {
          const config = {
            success: {
              icon: CheckCircle2,
              color: 'text-campus-green',
              surface: 'border-campus-green/25 bg-green-50',
              label: '成功',
            },
            error: {
              icon: CircleAlert,
              color: 'text-red-700',
              surface: 'border-red-200 bg-red-50',
              label: '错误',
            },
            info: {
              icon: Info,
              color: 'text-campus-gold',
              surface: 'border-campus-gold/25 bg-amber-50',
              label: '提示',
            },
          }[toast.type]
          const Icon = config.icon
          return (
            <div
              key={toast.id}
              role={toast.type === 'error' ? 'alert' : 'status'}
              aria-label={`${config.label}：${toast.message}`}
              className={`pointer-events-auto flex w-full items-start gap-2.5 rounded-card border px-3.5 py-3 shadow-panel ${config.surface} animate-slide-up`}
            >
              <Icon
                aria-hidden="true"
                className={`mt-0.5 size-[18px] shrink-0 ${config.color}`}
              />
              <span className="min-w-0 flex-1 text-sm leading-5 text-ink">
                {toast.message}
              </span>
              {toast.type === 'error' && (
                <button
                  type="button"
                  aria-label="关闭错误提示"
                  title="关闭"
                  onClick={() => dismiss(toast.id)}
                  className="icon-button -m-1 size-8"
                >
                  <X aria-hidden="true" className="size-4" />
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
