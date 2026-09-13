import { useRef, useState } from 'react'
import { ArrowLeft, CalendarClock, Heart, Link2, MapPin, RefreshCw, Share2, UsersRound } from 'lucide-react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { getExploreGroup, joinExploreGroup, setGroupFavorite } from '@/api/explore'
import ApplicationModal from '@/components/ApplicationModal'
import GroupHero from '@/components/details/GroupHero'
import ParticipantPreview from '@/components/details/ParticipantPreview'
import StickyActions from '@/components/details/StickyActions'
import { useDetailResource } from '@/components/details/useDetailResource'
import { useToast } from '@/components/Toast'
import type { ExploreGroupDetail } from '@shared/types'

async function shareCurrentPage(title: string) {
  const url = window.location.href
  if (navigator.share) {
    await navigator.share({ title, url })
    return
  }
  await navigator.clipboard?.writeText(url)
}

function displayValue(value: string | null) {
  return value?.trim() || '待确认'
}

export default function PostDetail() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const { showToast } = useToast()
  const { data: group, setData: setGroup, loading, error, retry } = useDetailResource(id, getExploreGroup)
  const [favoritePending, setFavoritePending] = useState(false)
  const [joinPending, setJoinPending] = useState(false)
  const [showApplication, setShowApplication] = useState(false)
  const [joinedTeam, setJoinedTeam] = useState<{ postId: string; teamId: string } | null>(null)
  const activeGroupId = useRef(id)
  activeGroupId.current = id

  const handleFavorite = async () => {
    if (!group || favoritePending) return
    const previousBookmark = group.bookmark
    const nextBookmark = !previousBookmark
    setFavoritePending(true)
    setGroup({ ...group, bookmark: nextBookmark })
    try {
      const result = await setGroupFavorite(group.id, nextBookmark)
      setGroup((current) => current?.id === group.id ? { ...current, bookmark: result.bookmark } : current)
    } catch {
      setGroup((current) => current?.id === group.id ? { ...current, bookmark: previousBookmark } : current)
      showToast('收藏失败，已恢复原状态', 'error')
    } finally {
      setFavoritePending(false)
    }
  }

  const handleDirectJoin = async () => {
    if (!group || joinPending) return
    setJoinPending(true)
    try {
      const result = await joinExploreGroup(group.id)
      if (activeGroupId.current !== group.id) return
      setGroup(result)
      setJoinedTeam({ postId: group.id, teamId: result.team_id })
      showToast('已加入组队', 'success')
    } catch {
      if (activeGroupId.current !== group.id) return
      showToast('加入失败，请刷新状态后重试', 'error')
    } finally {
      setJoinPending(false)
    }
  }

  const handleShare = async () => {
    if (!group) return
    try {
      await shareCurrentPage(group.title)
      showToast('分享内容已准备好', 'success')
    } catch {
      showToast('暂时无法分享，请稍后重试', 'error')
    }
  }

  if (loading) {
    return <div role="status" aria-label="正在加载组队详情" className="py-24 text-center text-sm text-ink-muted">正在加载组队详情...</div>
  }
  if (error || !group) return <DetailError onRetry={retry} />

  return (
    <div data-testid="group-detail-page" className="mx-auto min-w-0 max-w-5xl overflow-x-clip pb-[calc(9rem+env(safe-area-inset-bottom))] md:pb-8">
      <button type="button" onClick={() => navigate(-1)} className="mb-4 inline-flex min-h-10 items-center gap-1.5 text-sm font-semibold text-ink-muted transition-colors duration-fast hover:text-primary-700">
        <ArrowLeft aria-hidden="true" className="size-4" />返回
      </button>

      <GroupHero group={group} />

      <main className="space-y-8 py-8">
        <section aria-labelledby="group-facts-title">
          <p className="section-label">参与要求</p>
          <h2 id="group-facts-title" className="mt-2 text-xl font-bold text-ink">组队信息</h2>
          <dl className="mt-4 grid border-y border-stone bg-paper sm:grid-cols-2 lg:grid-cols-4">
            <Fact icon={UsersRound} label="队伍人数" value={`${group.current_members} / ${group.target_members} 人`} />
            <Fact icon={CalendarClock} label="截止时间" value={displayValue(group.deadline)} />
            <Fact icon={MapPin} label="参与范围" value={displayValue(group.school_scope)} />
            <Fact icon={CalendarClock} label="每周投入" value={displayValue(group.weekly_hours)} />
          </dl>
        </section>

        <section aria-labelledby="needed-roles-title" className="border-t border-stone pt-7">
          <p className="section-label">能力互补</p>
          <h2 id="needed-roles-title" className="mt-2 text-xl font-bold text-ink">所需角色</h2>
          <div className="mt-4 flex flex-wrap gap-2">
            {group.needed_roles.length > 0
              ? group.needed_roles.map((role) => <span key={role} className="tag-chip">{role}</span>)
              : <p className="text-sm text-ink-muted">角色不限，欢迎先聊聊。</p>}
          </div>
        </section>

        {group.linked_activity && (
          <section aria-labelledby="linked-activity-title" className="border-t border-stone pt-7">
            <p className="section-label">正式活动</p>
            <h2 id="linked-activity-title" className="mt-2 text-xl font-bold text-ink">关联活动</h2>
            <Link to={`/topics/${group.linked_activity.id}`} aria-label={`关联活动：${group.linked_activity.title}`} className="mt-4 flex min-w-0 items-center justify-between gap-4 rounded-card border border-stone bg-paper p-4 hover:border-primary-300">
              <span className="min-w-0">
                <span className="block break-words text-sm font-bold leading-6 text-ink">{group.linked_activity.title}</span>
                <span className="mt-1 block break-words text-xs leading-5 text-ink-muted">{group.linked_activity.organizer}</span>
              </span>
              <Link2 aria-hidden="true" className="size-4 shrink-0 text-primary-700" />
            </Link>
          </section>
        )}

        <ParticipantPreview people={group.member_preview} total={group.current_members} title="当前成员" itemLabel="成员" />

        {group.collaborators.length > 0 && (
          <section aria-labelledby="group-managers-title" className="border-t border-stone pt-7">
            <p className="section-label">协助管理</p>
            <h2 id="group-managers-title" className="mt-2 text-xl font-bold text-ink">组队负责人</h2>
            <p className="mt-4 text-sm leading-7 text-ink-muted">{group.collaborators.map((person) => `${person.nickname} · ${person.badge}`).join('，')}</p>
          </section>
        )}
      </main>

      <StickyActions label="组队操作">
        <button type="button" aria-label={group.bookmark ? '取消收藏组队' : '收藏组队'} title={group.bookmark ? '取消收藏组队' : '收藏组队'} disabled={favoritePending} onClick={handleFavorite} className="btn-secondary min-h-11 px-3 sm:px-4">
          <Heart aria-hidden="true" className="size-[18px]" fill={group.bookmark ? 'currentColor' : 'none'} /><span className="hidden sm:inline">{group.bookmark ? '已收藏' : '收藏'}</span>
        </button>
        <button type="button" aria-label="分享组队" title="分享组队" onClick={handleShare} className="btn-secondary min-h-11 px-3 sm:px-4">
          <Share2 aria-hidden="true" className="size-[18px]" /><span className="hidden sm:inline">分享</span>
        </button>
        <JoinAction group={group} joinedTeamId={joinedTeam?.postId === group.id ? joinedTeam.teamId : null} pending={joinPending} onApply={() => setShowApplication(true)} onDirectJoin={handleDirectJoin} />
      </StickyActions>

      {showApplication && (
        <ApplicationModal
          post={group}
          onClose={() => setShowApplication(false)}
          onSuccess={() => setGroup((current) => current ? { ...current, join_state: 'pending' } : current)}
        />
      )}
    </div>
  )
}

function JoinAction({
  group,
  joinedTeamId,
  pending,
  onApply,
  onDirectJoin,
}: {
  group: ExploreGroupDetail
  joinedTeamId: string | null
  pending: boolean
  onApply: () => void
  onDirectJoin: () => void
}) {
  if (group.join_state === 'owner') return <Link to="/profile?view=posts" className="btn-primary min-h-11">管理组队</Link>
  if (group.join_state === 'joined') {
    return joinedTeamId
      ? <Link to={`/teams/${joinedTeamId}`} className="btn-primary min-h-11">进入团队</Link>
      : <Link to="/profile?view=teams" className="btn-primary min-h-11">查看我的团队</Link>
  }
  if (group.join_state === 'pending') return <ActionState>申请审核中</ActionState>
  if (group.join_state === 'rejected') return <ActionState>申请未通过</ActionState>
  if (group.join_state === 'closed') return <ActionState>{group.status === 'full' ? '人数已满' : '暂不可加入'}</ActionState>
  if (group.join_mode === 'application') return <button type="button" onClick={onApply} className="btn-primary min-h-11">申请加入</button>
  if (group.join_mode === 'direct') return <button type="button" disabled={pending} onClick={onDirectJoin} className="btn-primary min-h-11">{pending ? '加入中...' : '直接加入'}</button>
  return <ActionState>仅供交流</ActionState>
}

function ActionState({ children }: { children: string }) {
  return <span aria-live="polite" className="flex min-h-11 items-center px-3 text-sm font-semibold text-ink-muted">{children}</span>
}

function Fact({ icon: Icon, label, value }: { icon: typeof UsersRound; label: string; value: string }) {
  return (
    <div className="flex min-w-0 gap-3 border-b border-stone px-4 py-4 last:border-b-0 sm:[&:nth-last-child(-n+2)]:border-b-0 lg:border-b-0 lg:border-r lg:last:border-r-0">
      <Icon aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-campus-green" />
      <div className="min-w-0"><dt className="text-xs text-ink-muted">{label}</dt><dd className="mt-1 break-words text-sm font-semibold leading-6 text-ink">{value}</dd></div>
    </div>
  )
}

function DetailError({ onRetry }: { onRetry: () => void }) {
  return (
    <div role="alert" className="mx-auto max-w-xl border-y border-stone bg-paper px-5 py-12 text-center">
      <p className="text-base font-semibold text-ink">组队加载失败</p>
      <p className="mt-2 text-sm text-ink-muted">网络可能暂时不可用，请重试。</p>
      <button type="button" onClick={onRetry} className="btn-primary mt-5 min-h-11"><RefreshCw aria-hidden="true" className="size-4" />重新加载</button>
    </div>
  )
}
