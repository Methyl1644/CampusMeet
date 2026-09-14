import { useCallback, useEffect, useMemo, useState } from 'react'
import { BadgeCheck, Building2, Crown, FileCheck2, RefreshCw, ShieldCheck, UsersRound } from 'lucide-react'
import type {
  OrganizationInvitationSummary,
  OwnershipTransferSummary,
  PlatformRoleGrant,
  TopicCollaborationInvitation,
  IdentitySummary,
  PostCollaborationInvitation,
  OrganizationApplicationSummary,
} from '@shared/types'
import { getProfile } from '@/api/auth'
import { getApiErrorMessage } from '@/api/auth-feedback'
import {
  acceptOrganizationInvitation,
  acceptOwnershipTransfer,
  acceptPlatformRole,
  acceptTopicCollaboration,
  acceptPostCollaboration,
  declineOrganizationInvitation,
  declineOwnershipTransfer,
  declinePlatformRole,
  declineTopicCollaboration,
  declinePostCollaboration,
  getMyOrganizationInvitations,
  getMyOwnershipTransfers,
  getMyPlatformRoles,
  getMyTopicCollaborations,
  getMyPostCollaborations,
  getMyOrganizationApplications,
  submitOrganizationApplication,
} from '@/api/authorizations'
import { useAuthStore } from '@/store/authStore'
import { publicUserId } from '@/features/identity/publicUserId'

const platformRoleLabels = { operator: '平台运营', senior_operator: '高级平台运营' }
const organizationRoleLabels = { publisher: '官方活动发布者', member: '组织成员' }
const topicRoleLabels = { manager: '活动负责人', editor: '活动组织者', coordinator: '活动协作成员' }
const postRoleLabels = { editor: '组队帖编辑者', application_manager: '加入申请管理员' }

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
  const [postInvitations, setPostInvitations] = useState<PostCollaborationInvitation[]>([])
  const [organizationApplications, setOrganizationApplications] = useState<OrganizationApplicationSummary[]>([])
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
      getProfile(),
      getMyPostCollaborations(),
      getMyOrganizationApplications(),
    ])
    if (results[0].status === 'fulfilled') setPlatformRoles(results[0].value.list.filter(({ status }) => status === 'pending'))
    if (results[1].status === 'fulfilled') setOrganizationInvitations(results[1].value.list.filter(({ status }) => status === 'pending'))
    if (results[2].status === 'fulfilled') setTopicInvitations(results[2].value.list.filter(({ status }) => status === 'pending'))
    if (results[3].status === 'fulfilled') setOwnershipTransfers(results[3].value.list.filter(({ status }) => status === 'pending'))
    if (results[4].status === 'fulfilled') setUser(results[4].value)
    if (results[5].status === 'fulfilled') setPostInvitations(results[5].value.list.filter(({ status }) => status === 'pending'))
    if (results[6].status === 'fulfilled') setOrganizationApplications(results[6].value.list)
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

  const pendingCount = useMemo(() => platformRoles.length + organizationInvitations.length + topicInvitations.length + postInvitations.length + ownershipTransfers.length, [platformRoles, organizationInvitations, topicInvitations, postInvitations, ownershipTransfers])

  return (
    <div className="mx-auto max-w-4xl animate-slide-up">
      <header className="flex flex-wrap items-end justify-between gap-4 border-b border-stone pb-6">
        <div><p className="section-label">身份确认</p><h1 className="mt-3 text-3xl font-bold text-ink">我的授权</h1><p className="mt-2 text-sm text-ink-muted">账号 ID：<strong className="text-ink">{publicUserId(user?.id || '')}</strong>。把它提供给工作人员即可接收授权邀请。</p></div>
        <button type="button" className="btn-secondary" disabled={loading} onClick={() => void load()}><RefreshCw aria-hidden="true" className="size-4" />刷新</button>
      </header>

      {error && <p role="alert" className="mt-5 rounded-card border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
      {user?.identity && <ActiveAuthorizations identity={user.identity} />}
      {user?.identity?.campus_verified && <OrganizationApplicationForm applications={organizationApplications} onSubmitted={load} />}
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

          <PendingSection title="组队帖协作者邀请" description="编辑者可以修改帖子，申请管理员可以协助处理加入申请。" icon={FileCheck2}>
            {postInvitations.length === 0 ? <EmptyAuthorization /> : postInvitations.map((invitation) => (
              <article key={`${invitation.post_id}-${invitation.role}`} className="flex flex-wrap items-center justify-between gap-4 rounded-card border border-stone p-4">
                <div><p className="font-bold text-ink">{invitation.post_title}</p><p className="mt-1 text-sm text-ink-muted">{postRoleLabels[invitation.role]}</p></div>
                <div className="flex gap-2"><button type="button" className="btn-secondary" disabled={Boolean(busyKey)} onClick={() => void run(`post-decline-${invitation.post_id}`, () => declinePostCollaboration(invitation.post_id))}>拒绝</button><button type="button" className="btn-primary" disabled={Boolean(busyKey)} onClick={() => void run(`post-accept-${invitation.post_id}`, () => acceptPostCollaboration(invitation.post_id))}>接受</button></div>
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
    ...identity.post_roles.map((item) => `${item.post_title} · ${postRoleLabels[item.role]}`),
  ]
  return (
    <section className="border-b border-stone py-6" aria-labelledby="active-authorizations-title">
      <h2 id="active-authorizations-title" className="text-lg font-bold text-ink">已生效身份</h2>
      {roles.length === 0 ? <p className="mt-3 text-sm text-ink-muted">当前只有普通校园用户权限</p> : <div className="mt-3 flex flex-wrap gap-2">{[...new Set(roles)].map((role) => <span key={role} className="rounded-full bg-primary-100 px-3 py-1.5 text-sm font-semibold text-primary-800">{role}</span>)}</div>}
    </section>
  )
}

function OrganizationApplicationForm({ applications, onSubmitted }: { applications: OrganizationApplicationSummary[]; onSubmitted: () => Promise<void> }) {
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [form, setForm] = useState({ organization_name: '', org_type: 'student_org' as const, school_scope: '南京大学', official_email: '', official_page: '', responsible_person_statement: '', evidence_reference: '' })
  const submit = async (event: React.FormEvent) => {
    event.preventDefault(); setBusy(true); setError('')
    try { await submitOrganizationApplication(form); setOpen(false); await onSubmitted() }
    catch (requestError) { setError(getApiErrorMessage(requestError, '认证申请提交失败')) }
    finally { setBusy(false) }
  }
  return <section className="border-b border-stone py-6" aria-labelledby="organization-application-title">
    <div className="flex flex-wrap items-center justify-between gap-3"><div><h2 id="organization-application-title" className="text-lg font-bold text-ink">组织官方认证</h2><p className="mt-1 text-sm text-ink-muted">学生组织、院系、实验室等可申请认证并获得正式活动发布身份。</p></div><button type="button" className="btn-secondary" onClick={() => setOpen((current) => !current)}><Building2 aria-hidden="true" className="size-4" />{open ? '收起申请' : '申请认证'}</button></div>
    {applications.length > 0 && <div className="mt-3 flex flex-wrap gap-2">{applications.map((item) => <span key={item.application_id} className="tag-chip">{item.organization_name} · {item.status}</span>)}</div>}
    {open && <form onSubmit={submit} className="mt-5 grid gap-4 sm:grid-cols-2">
      <label className="text-sm font-medium">组织名称<input required minLength={2} className="input-base mt-1.5" value={form.organization_name} onChange={(event) => setForm({ ...form, organization_name: event.target.value })} /></label>
      <label className="text-sm font-medium">组织类型<select className="input-base mt-1.5" value={form.org_type} onChange={(event) => setForm({ ...form, org_type: event.target.value as typeof form.org_type })}><option value="student_org">学生组织</option><option value="department">院系</option><option value="laboratory">实验室</option><option value="administrative">行政部门</option><option value="other">其他</option></select></label>
      <label className="text-sm font-medium">校内范围<input required minLength={2} className="input-base mt-1.5" value={form.school_scope} onChange={(event) => setForm({ ...form, school_scope: event.target.value })} /></label>
      <label className="text-sm font-medium">官方邮箱<input type="email" className="input-base mt-1.5" value={form.official_email} onChange={(event) => setForm({ ...form, official_email: event.target.value })} /></label>
      <label className="text-sm font-medium sm:col-span-2">官方主页（选填）<input type="url" className="input-base mt-1.5" value={form.official_page} onChange={(event) => setForm({ ...form, official_page: event.target.value })} /></label>
      <label className="text-sm font-medium sm:col-span-2">负责人说明<textarea required minLength={10} rows={3} className="input-base mt-1.5 resize-y" placeholder="说明你的身份、职责和申请理由" value={form.responsible_person_statement} onChange={(event) => setForm({ ...form, responsible_person_statement: event.target.value })} /></label>
      <label className="text-sm font-medium sm:col-span-2">证明材料链接或说明<textarea required rows={2} className="input-base mt-1.5 resize-y" value={form.evidence_reference} onChange={(event) => setForm({ ...form, evidence_reference: event.target.value })} /></label>
      {error && <p role="alert" className="text-sm text-red-700 sm:col-span-2">{error}</p>}
      <div className="sm:col-span-2"><button className="btn-primary" disabled={busy}>{busy ? '提交中...' : '提交认证申请'}</button></div>
    </form>}
  </section>
}
