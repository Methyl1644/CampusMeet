import { useState } from 'react'
import { ArrowLeft, ExternalLink, Heart, MessageCircle, Plus, RefreshCw, Share2, UserCog, UsersRound } from 'lucide-react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { getExploreActivity, setActivityFavorite } from '@/api/explore'
import ActivityFacts from '@/components/details/ActivityFacts'
import ActivityHero from '@/components/details/ActivityHero'
import ParticipantPreview from '@/components/details/ParticipantPreview'
import RelatedGroups from '@/components/details/RelatedGroups'
import StickyActions from '@/components/details/StickyActions'
import { useDetailResource } from '@/components/details/useDetailResource'
import { useToast } from '@/components/Toast'
import TopicCollaboratorsPanel from '@/features/management/TopicCollaboratorsPanel'
import { publicUserId } from '@/features/identity/publicUserId'
import type { ExploreActivityDetail } from '@shared/types'

async function shareCurrentPage(title: string) {
  const url = window.location.href
  if (navigator.share) {
    await navigator.share({ title, url })
    return
  }
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(url)
    return
  }
  throw new Error('Sharing is unavailable')
}

export default function TopicDetail() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const { showToast } = useToast()
  const { data: activity, setData: setActivity, loading, error, retry } = useDetailResource(id, getExploreActivity)
  const [favoritePending, setFavoritePending] = useState(false)
  const [showPersonnelManagement, setShowPersonnelManagement] = useState(false)

  const handleFavorite = async () => {
    if (!activity || favoritePending) return
    const previous = activity
    const nextFavorite = !(activity.favorite || activity.followed)
    setFavoritePending(true)
    setActivity({ ...activity, favorite: nextFavorite, followed: nextFavorite })
    try {
      const result = await setActivityFavorite(activity.id, nextFavorite)
      setActivity((current) => current?.id === activity.id
        ? { ...current, favorite: result.favorite, followed: result.followed, follower_count: result.follower_count }
        : current)
    } catch {
      setActivity((current) => current?.id === previous.id
        ? { ...current, favorite: previous.favorite, followed: previous.followed, follower_count: previous.follower_count }
        : current)
      showToast('收藏失败，已恢复原状态', 'error')
    } finally {
      setFavoritePending(false)
    }
  }

  const handleShare = async () => {
    if (!activity) return
    try {
      await shareCurrentPage(activity.title)
      showToast('分享内容已准备好', 'success')
    } catch {
      showToast('暂时无法分享，请稍后重试', 'error')
    }
  }

  if (loading) {
    return <div role="status" aria-label="正在加载活动详情" className="py-24 text-center text-sm text-ink-muted">正在加载活动详情...</div>
  }

  if (error || !activity) {
    return <DetailError label="活动加载失败" onRetry={retry} />
  }

  const favorite = activity.favorite || activity.followed

  return (
    <div data-testid="activity-detail-page" className="mx-auto min-w-0 max-w-5xl overflow-x-clip pb-[calc(9rem+env(safe-area-inset-bottom))] md:pb-8">
      <button type="button" onClick={() => navigate(-1)} className="mb-4 inline-flex min-h-10 items-center gap-1.5 text-sm font-semibold text-ink-muted transition-colors duration-fast hover:text-primary-700">
        <ArrowLeft aria-hidden="true" className="size-4" />返回
      </button>

      <ActivityHero activity={activity} />
      <ActivityFacts activity={activity} />

      <main className="space-y-8 py-8">
        <section aria-labelledby="activity-details-title">
          <p className="section-label">活动介绍</p>
          <h2 id="activity-details-title" className="mt-2 text-xl font-bold text-ink">活动详情</h2>
          <div className="mt-4 whitespace-pre-wrap break-words text-sm leading-8 text-ink">{activity.content || '活动详情待补充。'}</div>
          {activity.tags.length > 0 && (
            <div className="mt-5 flex flex-wrap gap-2" aria-label="活动标签">
              {activity.tags.map((tag) => <span key={tag.tag_id} className="tag-chip">{tag.canonical_name}</span>)}
            </div>
          )}
          {activity.source_url && (
            <a href={activity.source_url} target="_blank" rel="noreferrer" className="mt-5 inline-flex min-h-10 items-center gap-1.5 text-sm font-semibold text-primary-700 hover:text-primary-800">
              查看原始来源<ExternalLink aria-hidden="true" className="size-4" />
            </a>
          )}
        </section>

        <section aria-labelledby="activity-location-title" className="border-t border-stone pt-7">
          <p className="section-label">到达现场</p>
          <h2 id="activity-location-title" className="mt-2 text-xl font-bold text-ink">地点信息</h2>
          <p className="mt-4 break-words text-sm leading-7 text-ink-muted">
            <span>{activity.location_name || '具体地点待公布'}</span>
            {activity.campus_scope && <span> · {activity.campus_scope}</span>}
          </p>
        </section>

        <ParticipantPreview people={activity.participant_preview} total={activity.participant_count} />

        <section aria-label="活动工作人员与权限" className="border-t border-stone pt-7">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div><p className="section-label">组织与执行</p><h2 className="mt-2 text-xl font-bold text-ink">活动工作人员</h2></div>
            {activity.can_manage_collaborators && (
              <button type="button" className="btn-secondary" onClick={() => setShowPersonnelManagement((visible) => !visible)}>
                <UserCog aria-hidden="true" className="size-4" />{showPersonnelManagement ? '收起人员管理' : '管理活动人员'}
              </button>
            )}
          </div>
          {activity.responsible_people.length === 0 ? (
            <p className="mt-4 text-sm text-ink-muted">暂时没有可展示的活动工作人员。</p>
          ) : (
            <ul className="mt-4 divide-y divide-stone border-y border-stone">
              {activity.responsible_people.map((person) => (
                <li key={`${person.user_id}-${person.role}`} className="flex flex-wrap items-center justify-between gap-3 py-4">
                  <Link to={`/users/${person.user_id}`} className="min-w-0 font-semibold text-ink hover:text-primary-700">{person.nickname}</Link>
                  <span className="text-sm text-ink-muted">{person.badge} · {publicUserId(person.user_id)}</span>
                </li>
              ))}
            </ul>
          )}
        </section>

        {showPersonnelManagement && activity.can_manage_collaborators && (
          <section className="border-t border-stone pt-7">
            <TopicCollaboratorsPanel suggestedTopicId={activity.id} embedded />
          </section>
        )}
        <RelatedGroups groups={activity.related_groups} mode={activity.participation_mode} />
      </main>

      <StickyActions label="活动操作">
        <button type="button" aria-label={favorite ? '取消收藏活动' : '收藏活动'} title={favorite ? '取消收藏活动' : '收藏活动'} disabled={favoritePending} onClick={handleFavorite} className="btn-secondary min-h-11 px-3 sm:px-4">
          <Heart aria-hidden="true" className="size-[18px]" fill={favorite ? 'currentColor' : 'none'} /><span className="hidden sm:inline">{favorite ? '已收藏' : '收藏'}</span>
        </button>
        <button type="button" aria-label="分享活动" title="分享活动" onClick={handleShare} className="btn-secondary min-h-11 px-3 sm:px-4">
          <Share2 aria-hidden="true" className="size-[18px]" /><span className="hidden sm:inline">分享</span>
        </button>
        <ActivityPrimaryActions activity={activity} />
      </StickyActions>
    </div>
  )
}

function ActivityPrimaryActions({ activity }: { activity: ExploreActivityDetail }) {
  if (activity.participation_mode === 'open_team') {
    return (
      <>
        <a href="#related-groups" className="btn-secondary min-h-11"><UsersRound aria-hidden="true" className="size-4" />寻找队友</a>
        <Link to={`/publish?kind=topic_team&topic_id=${activity.id}`} className="btn-primary min-h-11"><Plus aria-hidden="true" className="size-4" />发布组队</Link>
      </>
    )
  }

  if (activity.participation_mode === 'official_signup') {
    const signup = activity.related_groups.find((group) => group.purpose === 'official_signup')
    return signup
      ? <Link to={`/posts/${signup.id}`} className="btn-primary min-h-11">进入官方报名</Link>
      : <span className="flex min-h-11 items-center px-3 text-sm font-semibold text-ink-muted">报名入口待发布</span>
  }

  return <a href="#related-groups" className="btn-primary min-h-11"><MessageCircle aria-hidden="true" className="size-4" />查看相关讨论</a>
}

function DetailError({ label, onRetry }: { label: string; onRetry: () => void }) {
  return (
    <div role="alert" className="mx-auto max-w-xl border-y border-stone bg-paper px-5 py-12 text-center">
      <p className="text-base font-semibold text-ink">{label}</p>
      <p className="mt-2 text-sm text-ink-muted">网络可能暂时不可用，页面内容没有丢失。</p>
      <button type="button" onClick={onRetry} className="btn-primary mt-5 min-h-11"><RefreshCw aria-hidden="true" className="size-4" />重新加载</button>
    </div>
  )
}
