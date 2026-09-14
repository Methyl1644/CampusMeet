import { useEffect, useState } from 'react'
import { Check, RefreshCw, X } from 'lucide-react'
import type { Application } from '@shared/types'
import { acceptApplication, getPostApplications, rejectApplication } from '@/api/applications'
import { getApiErrorMessage } from '@/api/auth-feedback'

export default function PostApplicationsPanel({ postId }: { postId: string }) {
  const [items, setItems] = useState<Application[]>([])
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const load = async () => {
    setError('')
    try { setItems(await getPostApplications(postId)) }
    catch (requestError) { setError(getApiErrorMessage(requestError, '加入申请暂时无法加载')) }
  }
  useEffect(() => { void load() }, [postId]) // eslint-disable-line react-hooks/exhaustive-deps

  const decide = async (applicationId: string, decision: 'accept' | 'reject') => {
    setBusy(applicationId); setError('')
    try { decision === 'accept' ? await acceptApplication(applicationId) : await rejectApplication(applicationId); await load() }
    catch (requestError) { setError(getApiErrorMessage(requestError, '申请处理失败')) }
    finally { setBusy('') }
  }

  return <section aria-labelledby="post-applications-title">
    <div className="flex items-center justify-between gap-3"><div><h3 id="post-applications-title" className="text-lg font-bold text-ink">加入申请</h3><p className="mt-1 text-sm text-ink-muted">发帖者和申请管理员可以共同处理。</p></div><button type="button" className="icon-button" title="刷新申请" onClick={() => void load()}><RefreshCw aria-hidden="true" className="size-4" /><span className="sr-only">刷新申请</span></button></div>
    {error && <p role="alert" className="mt-3 text-sm text-red-700">{error}</p>}
    <div className="mt-3 divide-y divide-stone border-y border-stone">{items.length === 0 ? <p className="py-5 text-sm text-ink-muted">暂无加入申请</p> : items.map((item) => <article key={item.id} className="grid gap-3 py-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center"><div><p className="font-semibold text-ink">{item.applicant.nickname} · {item.role_wanted}</p><p className="mt-1 text-sm text-ink-muted">{item.experience}</p><p className="mt-1 text-sm text-ink-muted">申请理由：{item.reason}</p></div>{item.status === 'pending' ? <div className="flex gap-2"><button type="button" className="btn-secondary" disabled={Boolean(busy)} onClick={() => void decide(item.id, 'reject')}><X aria-hidden="true" className="size-4" />拒绝</button><button type="button" className="btn-primary" disabled={Boolean(busy)} onClick={() => void decide(item.id, 'accept')}><Check aria-hidden="true" className="size-4" />接受</button></div> : <span className="text-sm font-semibold text-ink-muted">{item.status}</span>}</article>)}</div>
  </section>
}
