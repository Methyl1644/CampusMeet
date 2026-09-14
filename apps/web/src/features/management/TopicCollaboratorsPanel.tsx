import { useState, type FormEvent } from 'react'
import { RefreshCw, Search, Trash2, UserPlus } from 'lucide-react'
import type { CollaboratorGrant, TopicRole } from '@shared/types'
import {
  getTopicCollaborators,
  inviteTopicCollaborator,
  revokeTopicCollaborator,
} from '@/api/management'
import { getApiErrorMessage } from '@/api/auth-feedback'
import { parsePublicUserId, publicUserId } from '@/features/identity/publicUserId'

const roleDescriptions: Record<TopicRole, string> = {
  coordinator: '协作成员：处理报名与组队秩序',
  editor: '组织者：可维护活动信息',
  manager: '活动负责人：可增减活动协作者',
}

export default function TopicCollaboratorsPanel({ suggestedTopicId = '' }: { suggestedTopicId?: string }) {
  const [topicId, setTopicId] = useState(suggestedTopicId)
  const [activeTopicId, setActiveTopicId] = useState('')
  const [collaborators, setCollaborators] = useState<CollaboratorGrant[]>([])
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [userId, setUserId] = useState('')
  const [role, setRole] = useState<TopicRole>('coordinator')
  const [revokeUserId, setRevokeUserId] = useState<string | null>(null)

  const load = async (selectedId = topicId) => {
    const normalized = selectedId.trim()
    if (!normalized) {
      setError('请输入活动 ID')
      return
    }
    setLoading(true)
    setError('')
    try {
      setCollaborators((await getTopicCollaborators(normalized)).list)
      setActiveTopicId(normalized)
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, '活动协作者暂时无法加载'))
    } finally {
      setLoading(false)
    }
  }

  const invite = async (event: FormEvent) => {
    event.preventDefault()
    const parsedUserId = parsePublicUserId(userId)
    if (!activeTopicId || !parsedUserId) {
      setError('请先加载活动并输入有效的账号 ID，例如 CM-104')
      return
    }
    setBusy(true)
    setError('')
    try {
      await inviteTopicCollaborator(activeTopicId, { user_id: parsedUserId, role })
      setUserId('')
      await load(activeTopicId)
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, '活动协作者邀请失败'))
    } finally {
      setBusy(false)
    }
  }

  const revoke = async () => {
    if (!activeTopicId || !revokeUserId) return
    setBusy(true)
    setError('')
    try {
      await revokeTopicCollaborator(activeTopicId, revokeUserId)
      setRevokeUserId(null)
      await load(activeTopicId)
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, '活动协作者撤销失败'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section aria-labelledby="topic-collaborators-title">
      <div className="border-b border-stone pb-5">
        <h2 id="topic-collaborators-title" className="text-xl font-bold text-ink">活动协作者</h2>
        <p className="mt-1 text-sm text-ink-muted">输入官方活动 ID，设置负责人、组织者与协作成员。</p>
        <div className="mt-4 flex max-w-xl items-end gap-2">
          <label className="min-w-0 flex-1 text-sm font-medium text-ink">活动 ID
            <input className="input-base mt-1.5" value={topicId} onChange={(event) => setTopicId(event.target.value)} />
          </label>
          <button type="button" className="btn-primary" disabled={loading} onClick={() => void load()}><Search aria-hidden="true" className="size-4" />加载活动</button>
        </div>
      </div>

      {activeTopicId && (
        <form onSubmit={invite} className="grid gap-3 border-b border-stone py-5 sm:grid-cols-[minmax(0,1fr)_minmax(12rem,1fr)_auto] sm:items-end">
          <label className="text-sm font-medium">账号 ID<input className="input-base mt-1.5" placeholder="CM-104" value={userId} onChange={(event) => setUserId(event.target.value)} /></label>
          <label className="text-sm font-medium">活动身份<select className="input-base mt-1.5" value={role} onChange={(event) => setRole(event.target.value as TopicRole)}>{Object.entries(roleDescriptions).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
          <button type="submit" className="btn-primary" disabled={busy}><UserPlus aria-hidden="true" className="size-4" />发送邀请</button>
        </form>
      )}

      <div className="mt-4 grid gap-2 sm:grid-cols-3">
        {Object.entries(roleDescriptions).map(([value, label]) => <p key={value} className="rounded-card border border-stone px-3 py-2 text-xs text-ink-muted"><strong className="text-ink">{value}</strong><br />{label}</p>)}
      </div>

      {error && <p role="alert" className="my-4 rounded-card border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
      {loading ? <p role="status" className="py-10 text-center text-sm text-ink-muted">正在加载活动协作者...</p> : !activeTopicId ? (
        <p className="py-10 text-center text-sm text-ink-muted">加载一个活动后即可管理协作者</p>
      ) : collaborators.length === 0 ? (
        <p className="py-10 text-center text-sm text-ink-muted">该活动暂时没有协作者</p>
      ) : (
        <div className="divide-y divide-stone">
          {collaborators.map((grant) => (
            <div key={`${grant.user_id}-${grant.role}`} className="flex flex-wrap items-center justify-between gap-3 py-4">
              <div><p className="font-semibold text-ink">账号 {publicUserId(grant.user_id)}</p><p className="mt-1 text-sm text-ink-muted">{roleDescriptions[grant.role]} · {grant.status}</p></div>
              {grant.status === 'active' && (revokeUserId === grant.user_id ? (
                <div className="flex gap-2"><button type="button" className="btn-danger" disabled={busy} onClick={() => void revoke()}>确认撤销</button><button type="button" className="btn-secondary" onClick={() => setRevokeUserId(null)}>取消</button></div>
              ) : (
                <button type="button" className="icon-button text-red-700" title="撤销活动协作者" onClick={() => setRevokeUserId(grant.user_id)}><Trash2 aria-hidden="true" className="size-4" /><span className="sr-only">撤销活动协作者</span></button>
              ))}
            </div>
          ))}
        </div>
      )}
      {activeTopicId && <button type="button" className="btn-secondary mt-4" onClick={() => void load(activeTopicId)}><RefreshCw aria-hidden="true" className="size-4" />刷新协作者</button>}
    </section>
  )
}
