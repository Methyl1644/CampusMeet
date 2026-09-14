import { useEffect, useState, type FormEvent } from 'react'
import { RefreshCw, Trash2, UserPlus } from 'lucide-react'
import type { CollaboratorGrant, PostRole } from '@shared/types'
import { getPostCollaborators, invitePostCollaborator, revokePostCollaborator } from '@/api/management'
import { getApiErrorMessage } from '@/api/auth-feedback'
import { parsePublicUserId, publicUserId } from '@/features/identity/publicUserId'

const roleLabels: Record<PostRole, string> = {
  editor: '编辑者：可以修改组队帖内容',
  application_manager: '申请管理员：可以处理加入申请',
}

export default function PostCollaboratorsPanel({ postId }: { postId: string }) {
  const [items, setItems] = useState<CollaboratorGrant[]>([])
  const [userId, setUserId] = useState('')
  const [role, setRole] = useState<PostRole>('application_manager')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const load = async () => {
    try { setItems((await getPostCollaborators(postId)).list) }
    catch (requestError) { setError(getApiErrorMessage(requestError, '帖子协作者暂时无法加载')) }
  }
  useEffect(() => { void load() }, [postId]) // eslint-disable-line react-hooks/exhaustive-deps

  const invite = async (event: FormEvent) => {
    event.preventDefault()
    const parsed = parsePublicUserId(userId)
    if (!parsed) { setError('请输入有效账号 ID，例如 CM-104'); return }
    setBusy(true); setError('')
    try { await invitePostCollaborator(postId, { user_id: parsed, role }); setUserId(''); await load() }
    catch (requestError) { setError(getApiErrorMessage(requestError, '帖子协作者邀请失败')) }
    finally { setBusy(false) }
  }

  const revoke = async (targetId: string) => {
    if (!window.confirm(`确认撤销 ${publicUserId(targetId)} 的帖子权限吗？`)) return
    setBusy(true); setError('')
    try { await revokePostCollaborator(postId, targetId); await load() }
    catch (requestError) { setError(getApiErrorMessage(requestError, '权限撤销失败')) }
    finally { setBusy(false) }
  }

  return <section aria-labelledby="post-collaborators-title">
    <h3 id="post-collaborators-title" className="text-lg font-bold text-ink">组队帖协作者</h3>
    <p className="mt-1 text-sm text-ink-muted">邀请发出后，受邀者需在“我的授权”中接受。</p>
    <form onSubmit={invite} className="mt-4 grid gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(13rem,1fr)_auto] sm:items-end">
      <label className="text-sm font-medium">账号 ID<input className="input-base mt-1.5" placeholder="CM-104" value={userId} onChange={(event) => setUserId(event.target.value)} /></label>
      <label className="text-sm font-medium">权限<select className="input-base mt-1.5" value={role} onChange={(event) => setRole(event.target.value as PostRole)}>{Object.entries(roleLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
      <button className="btn-primary" disabled={busy}><UserPlus aria-hidden="true" className="size-4" />发送邀请</button>
    </form>
    {error && <p role="alert" className="mt-3 rounded-card border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
    <div className="mt-4 divide-y divide-stone border-y border-stone">
      {items.length === 0 ? <p className="py-5 text-sm text-ink-muted">暂无协作者</p> : items.map((item) => <div key={`${item.user_id}-${item.role}`} className="flex items-center justify-between gap-3 py-3"><p className="text-sm text-ink"><strong>{publicUserId(item.user_id)}</strong><span className="ml-2 text-ink-muted">{roleLabels[item.role as PostRole]} · {item.status}</span></p>{item.status !== 'revoked' && <button type="button" className="icon-button text-red-700" title="撤销权限" disabled={busy} onClick={() => void revoke(item.user_id)}><Trash2 aria-hidden="true" className="size-4" /><span className="sr-only">撤销权限</span></button>}</div>)}
    </div>
    <button type="button" className="btn-secondary mt-3" onClick={() => void load()}><RefreshCw aria-hidden="true" className="size-4" />刷新</button>
  </section>
}
