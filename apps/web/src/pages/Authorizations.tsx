import { useCallback, useEffect, useMemo, useState } from 'react'
import { BadgeCheck, Building2, Crown, RefreshCw, ShieldCheck, UsersRound } from 'lucide-react'
import type {
  OrganizationInvitationSummary,
  OwnershipTransferSummary,
  PlatformRoleGrant,
  TopicCollaborationInvitation,
  IdentitySummary,
} from '@shared/types'
import { getProfile } from '@/api/auth'
import { getApiErrorMessage } from '@/api/auth-feedback'
import {
  acceptOrganizationInvitation,
  acceptOwnershipTransfer,
  acceptPlatformRole,
  acceptTopicCollaboration,
  declineOrganizationInvitation,
  declineOwnershipTransfer,
  declinePlatformRole,
  declineTopicCollaboration,
  getMyOrganizationInvitations,
  getMyOwnershipTransfers,
  getMyPlatformRoles,
  getMyTopicCollaborations,
} from '@/api/authorizations'
import { useAuthStore } from '@/store/authStore'
import { publicUserId } from '@/features/identity/publicUserId'

const platformRoleLabels = { operator: '平台运营', senior_operator: '高级平台运营' }
const organizationRoleLabels = { publisher: '官方活动发布者', member: '组织成员' }
const topicRoleLabels = { manager: '活动负责人', editor: '活动组织者', coordinator: '活动协作成员' }

function PendingSection({ title, description, icon: Icon, children }: { title: string; description: string; icon: typeof BadgeCheck; children: React.ReactNode }) {
  return (
    <section className="border-b border-stone py-6 last:border-b-0" aria-labelledby={`${title}-title`}>
      <div className="flex items-start gap-3">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-card bg-primary-100 text-primary-700"><Icon aria-hidden="true" className="size-[18px]" /></span>
        <div><h2 id={`${title}-title`} className="text-lg font-bold text-ink">{title}</h2><p className="mt-1 text-sm text-ink-muted">{description}</p></div>
      </div>
      <div className="mt-4">{children}</div>
    </section>
  )
}

function EmptyAuthorization() {
  return <p className="py-4 text-sm text-ink-muted">暂无待处理邀请</p>
}

export default function Authorizations() {
  const setUser = useAuthStore((state) => state.setUser)
  const user = useAuthStore((state) => state.user)
  const [platformRoles, setPlatformRoles] = useState<PlatformRoleGrant[]>([])
  const [organizationInvitations, setOrganizationInvitations] = useState<OrganizationInvitationSummary[]>([])
  const [topicInvitations, setTopicInvitations] = useState<TopicCollaborationInvitation[]>([])
  const [ownershipTransfers, setOwnershipTransfers] = useState<OwnershipTransferSummary[]>([])
  const [passwords, setPasswords] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const [busyKey, setBusyKey] = useState('')
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    const results = await Promise.allSettled([
      getMyPlatformRoles(),
      getMyOrganizationInvitations(),
      getMyTopicCollaborations(),
      getMyOwnershipTransfers(),
    ])
    if (results[0].status === 'fulfilled') setPlatformRoles(results[0].value.list.filter(({ status }) => status === 'pending'))
    if (results[1].status === 'fulfilled') setOrganizationInvitations(results[1].value.list.filter(({ status }) => status === 'pending'))
    if (results[2].status === 'fulfilled') setTopicInvitations(results[2].value.list.filter(({ status }) => status === 'pending'))
    if (results[3].status === 'fulfilled') setOwnershipTransfers(results[3].value.list.filter(({ status }) => status === 'pending'))
    const failed = results.find((result) => result.status === 'rejected')
    if (failed?.status === 'rejected') setError(getApiErrorMessage(failed.reason, '部分授权邀请暂时无法加载'))
    setLoading(false)
  }, [])

  useEffect(() => { void load() }, [load])

  const refreshIdentity = async () => {
    setUser(await getProfile())
  }

  const run = async (key: string, operation: () => Promise<unknown>) => {
    setBusyKey(key)
    setError('')
    try {
      await operation()
      await refreshIdentity()
      await load()
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, '授权操作失败，请稍后重试'))
    } finally {
      setBusyKey('')
    }
  }

  const pendingCount = useMemo(() => platformRoles.length + organizationInvitations.length + topicInvitations.length + ownershipTransfers.length, [platformRoles, organizationInvitations, topicInvitations, ownershipTransfers])

  return (
    <div className="mx-auto max-w-4xl animate-slide-up">
      <header className="flex flex-wrap items-end justify-between gap-4 border-b border-stone pb-6">
        <div><p className="section-label">身份确认</p><h1 className="mt-3 text-3xl font-bold text-ink">我的授权</h1><p className="mt-2 text-sm text-ink-muted">账号 ID：<strong className="text-ink">{publicUserId(user?.id || '')}</strong>。把它提供给工作人员即可接收授权邀请。</p></div>
        <button type="button" className="btn-secondary" disabled={loading} onClick={() => void load()}><RefreshCw aria-hidden="true" className="size-4" />刷新</button>
      </header>

      {error && <p role="alert" className="mt-5 rounded-card border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
      {user?.identity && <ActiveAuthorizations identity={user.identity} />}
      {loading ? <p role="status" className="py-20 text-center text-sm text-ink-muted">正在读取授权邀请...</p> : pendingCount === 0 ? (
        <div className="py-20 text-center"><BadgeCheck aria-hidden="true" className="mx-auto size-10 text-campus-green" /><h2 className="mt-4 text-xl font-bold text-ink">所有授权都已处理</h2><p className="mt-2 text-sm text-ink-muted">收到新的身份邀请后会显示在这里。</p></div>
      ) : (
        <div>
          <PendingSection title="平台角色邀请" description="平台角色涉及全站管理，接受前需要重新验证当前密码。" icon={ShieldCheck}>
            {platformRoles.length === 0 ? <EmptyAuthorization /> : platformRoles.map((grant) => (
              <article key={grant.grant_id} className="grid gap-3 rounded-card border border-stone p-4 sm:grid-cols-[minmax(0,1fr)_minmax(12rem,0.7fr)_auto] sm:items-end">
                <div><p className="font-bold text-ink">{platformRoleLabels[grant.role]}</p><p className="mt-1 text-xs text-ink-muted">邀请人用户 #{grant.granted_by}</p></div>
                <label className="text-sm font-medium text-ink">当前密码<input type="password" className="input-base mt-1.5" autoComplete="current-password" value={passwords[grant.grant_id] || ''} onChange={(event) => setPasswords((current) => ({ ...current, [grant.grant_id]: event.target.value }))} /></label>
                <div className="flex gap-2"><button type="button" className="btn-secondary" disabled={Boolean(busyKey)} aria-label="拒绝平台角色" onClick={() => void run(`platform-decline-${grant.grant_id}`, () => declinePlatformRole(grant.grant_id))}>拒绝</button><button type="button" className="btn-primary" disabled={Boolean(busyKey) || (passwords[grant.grant_id] || '').length < 8} aria-label="接受平台角色" onClick={() => void run(`platform-accept-${grant.grant_id}`, () => acceptPlatformRole(grant.grant_id, passwords[grant.grant_id]))}>接受</button></div>
              </article>
            ))}
          </PendingSection>

          <PendingSection title="组织身份邀请" description="官方发布者可以代表认证组织发布官方活动，普通成员不具有发布权限。" icon={Building2}>
            {organizationInvitations.length === 0 ? <EmptyAuthorization /> : organizationInvitations.map((invitation) => (
              <article key={invitation.invitation_id} className="flex flex-wrap items-center justify-between gap-4 rounded-card border border-stone p-4">
                <div><p className="font-bold text-ink">{invitation.organization_name || `组织 #${invitation.organization_id}`}</p><p className="mt-1 text-sm text-ink-muted">{organizationRoleLabels[invitation.role]}</p></div>
                <div className="flex gap-2"><button type="button" className="btn-secondary" disabled={Boolean(busyKey)} aria-label="拒绝组织邀请" onClick={() => void run(`organization-decline-${invitation.invitation_id}`, () => declineOrganizationInvitation(invitation.invitation_id))}>拒绝</button><button type="button" className="btn-primary" disabled={Boolean(busyKey)} aria-label="接受组织邀请" onClick={() => void run(`organization-accept-${invitation.invitation_id}`, () => acceptOrganizationInvitation(invitation.invitation_id))}>接受</button></div>
              </article>
            ))}
          </PendingSection>

          <PendingSection title="活动协作者邀请" description="负责人可管理协作者，组织者可编辑活动，协作成员负责报名和组队秩序。" icon={UsersRound}>
            {topicInvitations.length === 0 ? <EmptyAuthorization /> : topicInvitations.map((invitation) => (
              <article key={`${invitation.topic_id}-${invitation.role}`} className="flex flex-wrap items-center justify-between gap-4 rounded-card border border-stone p-4">
                <div><p className="font-bold text-ink">{invitation.topic_title}</p><p className="mt-1 text-sm text-ink-muted">{topicRoleLabels[invitation.role]}</p></div>
                <div className="flex gap-2"><button type="button" className="btn-secondary" disabled={Boolean(busyKey)} aria-label="拒绝活动邀请" onClick={() => void run(`topic-decline-${invitation.topic_id}`, () => declineTopicCollaboration(invitation.topic_id))}>拒绝</button><button type="button" className="btn-primary" disabled={Boolean(busyKey)} aria-label="接受活动邀请" onClick={() => void run(`topic-accept-${invitation.topic_id}`, () => acceptTopicCollaboration(invitation.topic_id))}>接受</button></div>
              </article>
            ))}
          </PendingSection>

          <PendingSection title="负责人转移邀请" description="接受后你将成为组织负责人，并接管成员与官方发布者管理。" icon={Crown}>
            {ownershipTransfers.length === 0 ? <EmptyAuthorization /> : ownershipTransfers.map((transfer) => (
              <article key={transfer.transfer_id} className="flex flex-wrap items-center justify-between gap-4 rounded-card border border-stone p-4">
                <div><p className="font-bold text-ink">{transfer.organization_name || `组织 #${transfer.organization_id}`}</p><p className="mt-1 text-sm text-ink-muted">原负责人用户 #{transfer.from_owner_id}</p></div>
                <div className="flex gap-2"><button type="button" className="btn-secondary" disabled={Boolean(busyKey)} aria-label="拒绝负责人转移" onClick={() => void run(`transfer-decline-${transfer.transfer_id}`, () => declineOwnershipTransfer(transfer.transfer_id))}>拒绝</button><button type="button" className="btn-primary" disabled={Boolean(busyKey)} aria-label="接受负责人转移" onClick={() => void run(`transfer-accept-${transfer.transfer_id}`, () => acceptOwnershipTransfer(transfer.transfer_id))}>接受</button></div>
              </article>
            ))}
          </PendingSection>
        </div>
      )}
    </div>
  )
}

function ActiveAuthorizations({ identity }: { identity: IdentitySummary }) {
  const roles = [
    ...(identity.is_staff ? ['CampusMate 工作人员'] : []),
    ...(identity.platform_role ? [platformRoleLabels[identity.platform_role]] : []),
    ...identity.organization_roles.map((item) => `${item.organization_name} · ${item.role === 'owner' ? '负责人' : organizationRoleLabels[item.role as 'publisher' | 'member']}`),
    ...identity.topic_roles.map((item) => `${item.topic_title} · ${topicRoleLabels[item.role]}`),
  ]
  return (
    <section className="border-b border-stone py-6" aria-labelledby="active-authorizations-title">
      <h2 id="active-authorizations-title" className="text-lg font-bold text-ink">已生效身份</h2>
      {roles.length === 0 ? <p className="mt-3 text-sm text-ink-muted">当前只有普通校园用户权限</p> : <div className="mt-3 flex flex-wrap gap-2">{[...new Set(roles)].map((role) => <span key={role} className="rounded-full bg-primary-100 px-3 py-1.5 text-sm font-semibold text-primary-800">{role}</span>)}</div>}
    </section>
  )
}
