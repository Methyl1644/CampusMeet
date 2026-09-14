import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Crown, RefreshCw, Trash2, UserPlus } from 'lucide-react'
import type { ManagedOrganization, OrganizationMemberSummary } from '@shared/types'
import {
  getManagedOrganizations,
  getOrganizationMembers,
  inviteOrganizationMember,
  revokeOrganizationMember,
  transferOrganizationOwnership,
} from '@/api/management'
import { getApiErrorMessage } from '@/api/auth-feedback'
import { parsePublicUserId, publicUserId } from '@/features/identity/publicUserId'

export default function OrganizationMembersPanel() {
  const [organizations, setOrganizations] = useState<ManagedOrganization[]>([])
  const [organizationId, setOrganizationId] = useState('')
  const [members, setMembers] = useState<OrganizationMemberSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [inviteeId, setInviteeId] = useState('')
  const [inviteRole, setInviteRole] = useState<'publisher' | 'member'>('member')
  const [successorId, setSuccessorId] = useState('')
  const [revokeId, setRevokeId] = useState<string | null>(null)
  const [confirmTransfer, setConfirmTransfer] = useState(false)

  const loadMembers = useCallback(async (selectedId: string) => {
    if (!selectedId) {
      setMembers([])
      return
    }
    setLoading(true)
    setError('')
    try {
      setMembers((await getOrganizationMembers(selectedId)).list)
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, '组织成员暂时无法加载'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    let active = true
    void getManagedOrganizations()
      .then((items) => {
        if (!active) return
        setOrganizations(items)
        const firstId = items[0]?.organization_id || ''
        setOrganizationId(firstId)
        return loadMembers(firstId)
      })
      .catch((requestError) => {
        if (active) setError(getApiErrorMessage(requestError, '可管理组织暂时无法加载'))
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [loadMembers])

  const selectOrganization = (nextId: string) => {
    setOrganizationId(nextId)
    setRevokeId(null)
    setConfirmTransfer(false)
    void loadMembers(nextId)
  }

  const invite = async (event: FormEvent) => {
    event.preventDefault()
    const parsedUserId = parsePublicUserId(inviteeId)
    if (!organizationId || !parsedUserId) {
      setError('请选择组织并输入有效的账号 ID，例如 CM-104')
      return
    }
    setBusy(true)
    setError('')
    try {
      await inviteOrganizationMember(organizationId, { user_id: parsedUserId, role: inviteRole })
      setInviteeId('')
      await loadMembers(organizationId)
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, '组织成员邀请发送失败'))
    } finally {
      setBusy(false)
    }
  }

  const revoke = async () => {
    if (!organizationId || !revokeId) return
    setBusy(true)
    setError('')
    try {
      await revokeOrganizationMember(organizationId, revokeId)
      setRevokeId(null)
      await loadMembers(organizationId)
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, '成员权限撤销失败'))
    } finally {
      setBusy(false)
    }
  }

  const transfer = async () => {
    const parsedUserId = parsePublicUserId(successorId)
    if (!organizationId || !parsedUserId) {
      setError('请输入有效的接任账号 ID，例如 CM-104')
      return
    }
    if (!confirmTransfer) {
      setConfirmTransfer(true)
      return
    }
    setBusy(true)
    setError('')
    try {
      await transferOrganizationOwnership(organizationId, String(parsedUserId))
      setSuccessorId('')
      setConfirmTransfer(false)
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, '负责人转移邀请发送失败'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section aria-labelledby="organization-members-title">
      <div className="flex flex-wrap items-end justify-between gap-4 border-b border-stone pb-5">
        <div>
          <h2 id="organization-members-title" className="text-xl font-bold text-ink">组织成员</h2>
          <p className="mt-1 text-sm text-ink-muted">负责人可邀请成员和官方活动发布者，也可以发起负责人转移。</p>
        </div>
        <label className="min-w-56 text-sm font-medium text-ink">当前组织
          <select className="input-base mt-1.5" value={organizationId} onChange={(event) => selectOrganization(event.target.value)}>
            {organizations.length === 0 && <option value="">暂无可管理组织</option>}
            {organizations.map((organization) => <option key={organization.organization_id} value={organization.organization_id}>{organization.organization_name}</option>)}
          </select>
        </label>
      </div>

      {organizationId && (
        <div className="grid gap-6 border-b border-stone py-5 lg:grid-cols-2">
          <form onSubmit={invite}>
            <h3 className="font-bold text-ink">邀请成员</h3>
            <div className="mt-3 grid gap-3 sm:grid-cols-[minmax(0,1fr)_10rem_auto] sm:items-end">
              <label className="text-sm font-medium">账号 ID<input className="input-base mt-1.5" placeholder="CM-104" value={inviteeId} onChange={(event) => setInviteeId(event.target.value)} /></label>
              <label className="text-sm font-medium">组织身份<select className="input-base mt-1.5" value={inviteRole} onChange={(event) => setInviteRole(event.target.value as 'publisher' | 'member')}><option value="member">普通成员</option><option value="publisher">官方发布者</option></select></label>
              <button type="submit" className="btn-primary" disabled={busy}><UserPlus aria-hidden="true" className="size-4" />发送邀请</button>
            </div>
          </form>
          <div>
            <h3 className="font-bold text-ink">转移负责人</h3>
            <div className="mt-3 flex flex-wrap items-end gap-3">
              <label className="min-w-48 flex-1 text-sm font-medium">接任账号 ID<input className="input-base mt-1.5" placeholder="CM-104" value={successorId} onChange={(event) => { setSuccessorId(event.target.value); setConfirmTransfer(false) }} /></label>
              <button type="button" className={confirmTransfer ? 'btn-danger' : 'btn-secondary'} disabled={busy} onClick={() => void transfer()}><Crown aria-hidden="true" className="size-4" />{confirmTransfer ? '确认发送转移邀请' : '发起转移'}</button>
            </div>
          </div>
        </div>
      )}

      {error && <p role="alert" className="my-4 rounded-card border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
      {loading ? <p role="status" className="py-10 text-center text-sm text-ink-muted">正在加载组织成员...</p> : !organizationId ? (
        <p className="py-10 text-center text-sm text-ink-muted">你目前不是任何已认证组织的负责人</p>
      ) : members.length === 0 ? (
        <p className="py-10 text-center text-sm text-ink-muted">该组织暂时没有成员记录</p>
      ) : (
        <div className="divide-y divide-stone">
          {members.map((member) => (
            <div key={`${member.user_id}-${member.role}`} className="flex flex-wrap items-center justify-between gap-3 py-4">
              <div><p className="font-semibold text-ink">账号 {publicUserId(member.user_id)}</p><p className="mt-1 text-sm text-ink-muted">{member.role} · {member.status}</p></div>
              {member.role !== 'owner' && member.status === 'active' && (
                revokeId === member.user_id ? (
                  <div className="flex gap-2"><button type="button" className="btn-danger" disabled={busy} onClick={() => void revoke()}>确认撤销</button><button type="button" className="btn-secondary" onClick={() => setRevokeId(null)}>取消</button></div>
                ) : (
                  <button type="button" className="icon-button text-red-700" title="撤销成员权限" onClick={() => setRevokeId(member.user_id)}><Trash2 aria-hidden="true" className="size-4" /><span className="sr-only">撤销成员权限</span></button>
                )
              )}
            </div>
          ))}
        </div>
      )}
      {organizationId && <button type="button" className="btn-secondary mt-4" onClick={() => void loadMembers(organizationId)}><RefreshCw aria-hidden="true" className="size-4" />刷新成员</button>}
    </section>
  )
}
