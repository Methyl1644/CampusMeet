import { useState } from 'react'
import { Image, UserRound } from 'lucide-react'
import type { ExploreGroupDetail, PostPurpose } from '@shared/types'

const purposeLabels: Record<PostPurpose, string> = {
  team_recruitment: '招募队友',
  official_signup: '官方报名',
  discussion: '讨论',
}

export default function GroupHero({ group }: { group: ExploreGroupDetail }) {
  const [failedCoverUrl, setFailedCoverUrl] = useState<string | null>(null)
  const showCover = Boolean(group.cover_url) && failedCoverUrl !== group.cover_url

  return (
    <header className="grid min-w-0 gap-6 border-y border-stone bg-paper px-4 py-6 sm:px-7 lg:grid-cols-[minmax(0,1fr)_minmax(20rem,0.72fr)] lg:items-center lg:gap-10 lg:py-8">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-[#EAF3F0] px-2.5 py-1 text-xs font-semibold text-campus-green">{purposeLabels[group.purpose]}</span>
          <span className="text-xs font-medium text-ink-muted">{group.main_category}</span>
        </div>
        <h1 className="mt-4 break-words text-2xl font-bold leading-9 text-ink sm:text-3xl sm:leading-10">{group.title}</h1>
        <p className="mt-4 whitespace-pre-wrap break-words text-sm leading-7 text-ink-muted">{group.description || '发起人暂未补充说明。'}</p>
        <div className="mt-5 flex min-w-0 items-center gap-2 text-sm text-ink">
          <UserRound aria-hidden="true" className="size-4 shrink-0 text-campus-green" />
          <span className="truncate font-semibold">{group.author?.nickname || '发起人待确认'}</span>
          {group.author && <span className="truncate text-xs text-ink-muted">{[group.author.major, group.author.grade].filter(Boolean).join(' · ')}</span>}
        </div>
      </div>
      <div data-testid="group-detail-media" className="aspect-[16/9] min-w-0 overflow-hidden rounded-card bg-[#E8EDF2]">
        {showCover ? (
          <img src={group.cover_url ?? undefined} alt={`${group.title}封面`} onError={() => setFailedCoverUrl(group.cover_url)} className="size-full object-cover" />
        ) : (
          <span role="img" aria-label="组队封面占位图" className="flex size-full items-center justify-center text-[#31576B]"><Image aria-hidden="true" className="size-12" /></span>
        )}
      </div>
    </header>
  )
}
