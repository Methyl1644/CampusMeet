import { AlertCircle, RefreshCw } from 'lucide-react'
import DeadlineReminder from '@/components/home/DeadlineReminder'
import GroupTimeline from '@/components/home/GroupTimeline'
import HomeSkeleton from '@/components/home/HomeSkeleton'
import MyEventsSummary from '@/components/home/MyEventsSummary'
import MyGroupsSummary from '@/components/home/MyGroupsSummary'
import ProfileSummary from '@/components/home/ProfileSummary'
import RecommendationRail from '@/components/home/RecommendationRail'
import { useHomeFeed } from '@/features/home/HomeFeedContext'

export default function Home() {
  const { feed, loading, error, reload } = useHomeFeed()

  if (!feed && loading) return <HomeSkeleton />

  if (!feed && error) {
    return (
      <section role="alert" className="mx-auto flex min-h-[24rem] max-w-xl flex-col items-center justify-center text-center">
        <span className="flex size-12 items-center justify-center rounded-full bg-primary-100 text-primary-700">
          <AlertCircle aria-hidden="true" className="size-6" />
        </span>
        <h1 className="mt-4 text-xl font-bold text-ink">首页暂时无法加载</h1>
        <p className="mt-2 text-sm leading-6 text-ink-muted">请检查网络连接后再试一次。</p>
        <button type="button" onClick={() => void reload()} className="btn-primary mt-5">
          <RefreshCw aria-hidden="true" className="size-4" />
          重新加载首页
        </button>
      </section>
    )
  }

  if (!feed) return <HomeSkeleton />

  const recommendedDegraded = feed.warnings.includes('recommended_topics')
  const timelineDegraded = feed.warnings.includes('group_timeline')
  const followedDegraded = feed.warnings.includes('followed_topics')
  const attendingDegraded = feed.warnings.includes('attending_topics')
  const groupsDegraded = feed.warnings.includes('joined_groups')
  const deadlineDegraded = feed.warnings.includes('deadline_reminder')

  return (
    <div aria-busy={loading} className="animate-slide-up">
      <h1 className="sr-only">你的 CampusMate 首页</h1>
      <div className="grid min-w-0 grid-cols-1 gap-8 lg:grid-cols-[minmax(0,280px)_minmax(0,1fr)] lg:gap-10">
        <aside aria-label="我的首页摘要" className="min-w-0 space-y-5">
          <ProfileSummary profile={feed.profile} />
          {followedDegraded || attendingDegraded ? (
            <UnavailableSummary title="我的活动" message="活动摘要暂时无法加载" />
          ) : (
            <MyEventsSummary attending={feed.attending_topics} saved={feed.followed_topics} />
          )}
          {groupsDegraded ? (
            <UnavailableSummary title="我的小组" message="小组摘要暂时无法加载" />
          ) : (
            <MyGroupsSummary groups={feed.joined_groups} />
          )}
        </aside>

        <div className="min-w-0 overflow-hidden">
          {deadlineDegraded ? (
            <p role="status" className="mb-4 text-xs text-ink-muted">
              截止提醒暂时无法加载
            </p>
          ) : feed.deadline_reminder ? (
            <div className="mb-7">
              <DeadlineReminder reminder={feed.deadline_reminder} />
            </div>
          ) : null}
          <RecommendationRail topics={feed.recommended_topics} degraded={recommendedDegraded} />
          <div className="mt-10 sm:mt-12">
            <GroupTimeline items={feed.group_timeline} degraded={timelineDegraded} />
          </div>
        </div>
      </div>
    </div>
  )
}

function UnavailableSummary({ title, message }: { title: string; message: string }) {
  return (
    <section className="min-h-28 rounded-card border border-stone bg-paper p-4 shadow-panel">
      <h2 className="text-base font-semibold text-ink">{title}</h2>
      <p role="status" className="mt-4 text-sm text-ink-muted">{message}</p>
    </section>
  )
}
