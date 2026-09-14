import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { PauseCircle, RefreshCw, ShieldPlus, Trash2 } from 'lucide-react'
import type { PlatformRole, PlatformRoleGrant } from '@shared/types'
import {
  getPlatformRoles,
  invitePlatformRole,
  revokePlatformRole,
  suspendPlatformRole,
} from '@/api/management'
import { getApiErrorMessage } from '@/api/auth-feedback'
import { parsePublicUserId, publicUserId } from '@/features/identity/publicUserId'

const roleLabel: Record<PlatformRole, string> = {
  operator: '平台运营',
  senior_operator: '高级平台运营',
}

export default function PlatformRolesPanel({ canManage }: { canManage: boolean }) {
  const [roles, setRoles] = useState<PlatformRoleGrant[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [userId, setUserId] = useState('')
  const [role, setRole] = useState<PlatformRole>('operator')
  const [confirmAction, setConfirmAction] = useState<{ id: string; kind: 'suspend' | 'revoke' } | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setRoles((await getPlatformRoles()).list)
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, '平台角色暂时无法加载'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  const invite = async (event: FormEvent) => {
    event.preventDefault()
    const parsedUserId = parsePublicUserId(userId)
    if (!parsedUserId) {
      setError('请输入有效的账号 ID，例如 CM-104')
      return
    }
    setBusy(true)
    setError('')
    try {
      await invitePlatformRole({ user_id: parsedUserId, role })
      setUserId('')
      await load()
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, '角色邀请发送失败'))
    } finally {
      setBusy(false)
    }
  }

  const runConfirmedAction = async () => {
    if (!confirmAction) return
    setBusy(true)
    setError('')
    try {
      const reason = confirmAction.kind === 'suspend' ? '由高级运营在管理中心暂停' : '由高级运营在管理中心撤销'
      if (confirmAction.kind === 'suspend') {
        await suspendPlatformRole(confirmAction.id, reason)
      } else {
        await revokePlatformRole(confirmAction.id, reason)
      }
      setConfirmAction(null)
      await load()
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, '平台角色操作失败'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section aria-labelledby="platform-roles-title">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-stone pb-5">
        <div>
          <h2 id="platform-roles-title" className="text-xl font-bold text-ink">平台角色</h2>
          <p className="mt-1 text-sm text-ink-muted">平台运营负责组织审核；高级平台运营可增减运营成员。</p>
        </div>
        <button type="button" className="icon-button" title="刷新平台角色" onClick={() => void load()}>
          <RefreshCw aria-hidden="true" className="size-4" />
          <span className="sr-only">刷新平台角色</span>
        </button>
      </div>

      {canManage && (
        <form onSubmit={invite} className="grid gap-3 border-b border-stone py-5 sm:grid-cols-[minmax(0,1fr)_12rem_auto] sm:items-end">
          <label className="text-sm font-medium text-ink">账号 ID
            <input className="input-base mt-1.5" value={userId} onChange={(event) => setUserId(event.target.value)} placeholder="CM-104" />
          </label>
          <label className="text-sm font-medium text-ink">平台角色
            <select className="input-base mt-1.5" value={role} onChange={(event) => setRole(event.target.value as PlatformRole)}>
              <option value="operator">平台运营</option>
              <option value="senior_operator">高级平台运营</option>
            </select>
          </label>
          <button type="submit" className="btn-primary" disabled={busy}>
            <ShieldPlus aria-hidden="true" className="size-4" />发送角色邀请
          </button>
        </form>
      )}

      {error && <p role="alert" className="my-4 rounded-card border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
      {loading ? <p role="status" className="py-10 text-center text-sm text-ink-muted">正在加载平台角色...</p> : roles.length === 0 ? (
        <p className="py-10 text-center text-sm text-ink-muted">暂时没有平台角色记录</p>
      ) : (
        <div className="divide-y divide-stone">
          {roles.map((grant) => (
            <div key={grant.grant_id} className="flex flex-wrap items-center justify-between gap-3 py-4">
              <div className="min-w-0">
                <p className="font-semibold text-ink">账号 {publicUserId(grant.user_id)}</p>
                <p className="mt-1 text-sm text-ink-muted">{roleLabel[grant.role]} · {grant.status}</p>
              </div>
              {canManage && grant.status === 'active' && (
                confirmAction?.id === grant.grant_id ? (
                  <div className="flex items-center gap-2" role="group" aria-label="确认平台角色操作">
                    <button type="button" className="btn-danger" disabled={busy} onClick={() => void runConfirmedAction()}>确认</button>
                    <button type="button" className="btn-secondary" onClick={() => setConfirmAction(null)}>取消</button>
                  </div>
                ) : (
                  <div className="flex items-center gap-1">
                    <button type="button" className="icon-button" title="暂停角色" onClick={() => setConfirmAction({ id: grant.grant_id, kind: 'suspend' })}>
                      <PauseCircle aria-hidden="true" className="size-4" /><span className="sr-only">暂停角色</span>
                    </button>
                    <button type="button" className="icon-button text-red-700" title="撤销角色" onClick={() => setConfirmAction({ id: grant.grant_id, kind: 'revoke' })}>
                      <Trash2 aria-hidden="true" className="size-4" /><span className="sr-only">撤销角色</span>
                    </button>
                  </div>
                )
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
