import { ArrowUpRight, MessageCircle, UsersRound } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { ExploreGroupCard, ParticipationMode, PostPurpose } from '@shared/types'

const purposeLabels: Record<PostPurpose, string> = {
  team_recruitment: '招募队友',
  official_signup: '官方报名',
  discussion: '讨论',
}

const emptyCopy: Record<ParticipationMode, string> = {
  open_team: '还没有相关组队，成为第一个发起人。',
  official_signup: '官方报名入口暂未发布，请关注活动更新。',
  information_only: '暂时没有相关讨论。',
}

export default function RelatedGroups({
  groups,
  mode,
}: {
  groups: ExploreGroupCard[]
  mode: ParticipationMode
}) {
  const purposeForMode: Record<ParticipationMode, PostPurpose> = {
    open_team: 'team_recruitment',
    official_signup: 'official_signup',
    information_only: 'discussion',
  }
  const visibleGroups = groups
    .filter((group) => group.purpose === purposeForMode[mode])
    .slice(0, 8)

  return (
    <section id="related-groups" aria-labelledby="related-groups-title" className="scroll-mt-28 border-t border-stone pt-7">
      <p className="section-label">继续参与</p>
      <h2 id="related-groups-title" className="mt-2 text-xl font-bold text-ink">
        {mode === 'official_signup' ? '官方报名' : mode === 'information_only' ? '相关讨论' : '关联组队'}
      </h2>
      {visibleGroups.length > 0 ? (
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {visibleGroups.map((group) => (
            <article key={group.id} className="flex min-w-0 flex-col rounded-card border border-stone bg-paper p-4">
              <div className="flex items-center justify-between gap-3">
                <span className="rounded-full bg-[#EAF3F0] px-2.5 py-1 text-xs font-semibold text-campus-green">{purposeLabels[group.purpose]}</span>
                <span className="inline-flex shrink-0 items-center gap-1 text-xs text-ink-muted"><UsersRound aria-hidden="true" className="size-3.5" />{group.current_members}/{group.target_members}</span>
              </div>
              <h3 className="mt-3 break-words text-base font-bold leading-6 text-ink">{group.title}</h3>
              <p className="mt-2 line-clamp-2 text-sm leading-6 text-ink-muted">{group.description || '暂无补充说明'}</p>
              <Link to={`/posts/${group.id}`} className="mt-4 inline-flex min-h-9 items-center gap-1 self-start text-sm font-semibold text-primary-700 hover:text-primary-800">
                查看详情<ArrowUpRight aria-hidden="true" className="size-4" />
              </Link>
            </article>
          ))}
        </div>
      ) : (
        <div className="mt-4 flex items-start gap-2 border-y border-stone py-6 text-sm text-ink-muted">
          <MessageCircle aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
          <p>{emptyCopy[mode]}</p>
        </div>
      )}
    </section>
  )
}
