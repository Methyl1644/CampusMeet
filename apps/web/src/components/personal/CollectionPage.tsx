import { AlertCircle, RefreshCw } from 'lucide-react'
import type { ReactNode } from 'react'
import EmptyState from '@/components/EmptyState'

export default function CollectionPage({
  title,
  eyebrow,
  description,
  tabs,
  loading,
  error,
  empty,
  hasMore,
  loadingMore,
  onRetry,
  onLoadMore,
  children,
}: {
  title: string
  eyebrow: string
  description: string
  tabs: ReactNode
  loading: boolean
  error: boolean
  empty: boolean
  hasMore: boolean
  loadingMore: boolean
  onRetry: () => void
  onLoadMore: () => void
  children: ReactNode
}) {
  return (
    <div className="animate-slide-up">
      <header className="border-b border-stone pb-6">
        <p className="section-label">{eyebrow}</p>
        <h1 className="mt-3 text-3xl font-bold text-ink">{title}</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-ink-muted">{description}</p>
      </header>
      <div className="mt-6">{tabs}</div>
      {loading ? (
        <div role="status" className="grid min-h-64 place-items-center text-sm text-ink-muted">正在加载...</div>
      ) : error ? (
        <section role="alert" className="grid min-h-64 place-items-center text-center">
          <div>
            <AlertCircle aria-hidden="true" className="mx-auto size-8 text-primary-700" />
            <p className="mt-3 font-semibold text-ink">内容暂时无法加载</p>
            <button type="button" className="btn-secondary mt-4" onClick={onRetry}><RefreshCw aria-hidden="true" className="size-4" />重试</button>
          </div>
        </section>
      ) : empty ? (
        <EmptyState title="这里还没有内容" />
      ) : (
        <>
          {children}
          {hasMore && (
            <div className="mt-8 flex justify-center">
              <button type="button" className="btn-secondary" disabled={loadingMore} onClick={onLoadMore}>
                {loadingMore ? '加载中...' : '加载更多'}
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
