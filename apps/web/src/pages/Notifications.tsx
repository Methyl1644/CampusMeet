import { useCallback, useEffect, useState } from 'react'
import { CheckCheck, RefreshCw } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import EmptyState from '@/components/EmptyState'
import NotificationItem, { notificationTarget } from '@/components/personal/NotificationItem'
import { getNotifications, markAllNotificationsRead, markNotificationRead } from '@/api/notifications'
import { useHomeFeed } from '@/features/home/HomeFeedContext'
import { useToast } from '@/components/Toast'
import type { Notification } from '@shared/types'

export default function Notifications() {
  const navigate = useNavigate()
  const { setNotificationUnread } = useHomeFeed()
  const { showToast } = useToast()
  const [items, setItems] = useState<Notification[]>([])
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [pending, setPending] = useState(false)

  const load = useCallback(async (nextPage = 1, append = false) => {
    if (!append) setLoading(true)
    setError(false)
    try {
      const result = await getNotifications(nextPage, 20)
      setItems((current) => append ? [...current, ...result.list.filter((item) => !current.some((known) => known.id === item.id))] : result.list)
      setPage(result.page)
      setPages(result.pages)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  const open = async (item: Notification) => {
    const target = notificationTarget(item)
    if (!item.read_at) {
      const before = items
      const optimistic = items.map((entry) => entry.id === item.id ? { ...entry, read_at: new Date().toISOString() } : entry)
      setItems(optimistic)
      setNotificationUnread(optimistic.filter((entry) => !entry.read_at).length)
      try {
        const result = await markNotificationRead(item.id)
        if (typeof result.unread_count === 'number') setNotificationUnread(result.unread_count)
      } catch {
        setItems(before)
        setNotificationUnread(before.filter((entry) => !entry.read_at).length)
        showToast('通知状态更新失败', 'error')
        return
      }
    }
    if (target) navigate(target)
  }

  const readAll = async () => {
    if (pending || items.every((item) => item.read_at)) return
    const before = items
    setPending(true)
    setItems((current) => current.map((item) => ({ ...item, read_at: item.read_at ?? new Date().toISOString() })))
    setNotificationUnread(0)
    try {
      const result = await markAllNotificationsRead()
      setNotificationUnread(result.unread_count ?? 0)
    } catch {
      setItems(before)
      setNotificationUnread(before.filter((item) => !item.read_at).length)
      showToast('全部标为已读失败', 'error')
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="mx-auto max-w-4xl animate-slide-up">
      <header className="flex flex-wrap items-end justify-between gap-4 border-b border-stone pb-6">
        <div>
          <p className="section-label">信息中心</p>
          <h1 className="mt-3 text-3xl font-bold text-ink">通知</h1>
        </div>
        <button type="button" className="btn-secondary" disabled={pending || items.every((item) => item.read_at)} onClick={readAll}>
          <CheckCheck aria-hidden="true" className="size-4" />全部标为已读
        </button>
      </header>
      {loading ? (
        <div role="status" className="grid min-h-72 place-items-center text-sm text-ink-muted">正在加载通知...</div>
      ) : error ? (
        <div role="alert" className="grid min-h-72 place-items-center text-center"><div><p className="font-semibold">通知暂时无法加载</p><button type="button" className="btn-secondary mt-4" onClick={() => void load()}><RefreshCw aria-hidden="true" className="size-4" />重试</button></div></div>
      ) : items.length === 0 ? (
        <EmptyState title="暂时没有新通知" />
      ) : (
        <div aria-live="polite">{items.map((item) => <NotificationItem key={item.id} item={item} onOpen={open} />)}</div>
      )}
      {page < pages && !loading && !error && <div className="mt-6 flex justify-center"><button type="button" className="btn-secondary" onClick={() => void load(page + 1, true)}>加载更多</button></div>}
    </div>
  )
}
