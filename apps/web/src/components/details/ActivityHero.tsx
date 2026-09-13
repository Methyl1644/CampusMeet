import { useState } from 'react'
import { Building2, Image, ShieldCheck } from 'lucide-react'
import type { ExploreActivityDetail } from '@shared/types'

export default function ActivityHero({ activity }: { activity: ExploreActivityDetail }) {
  const [failedCoverUrl, setFailedCoverUrl] = useState<string | null>(null)
  const showCover = Boolean(activity.cover_url) && failedCoverUrl !== activity.cover_url

  return (
    <header className="grid min-w-0 gap-6 border-y border-stone bg-paper px-4 py-6 sm:px-7 lg:grid-cols-[minmax(0,1fr)_minmax(22rem,0.82fr)] lg:items-center lg:gap-10 lg:py-8">
      <div className="min-w-0 lg:py-3">
        <div className="flex flex-wrap items-center gap-2 text-xs font-semibold text-campus-green">
          {activity.trust_badges.map((badge) => (
            <span key={`${badge.kind}-${badge.label}`} className="inline-flex items-center gap-1.5 rounded-full bg-[#EAF3F0] px-2.5 py-1">
              <ShieldCheck aria-hidden="true" className="size-3.5" />
              {badge.label}
            </span>
          ))}
          <span className="text-ink-muted">{activity.edition}</span>
        </div>
        <h1 className="mt-4 break-words text-2xl font-bold leading-9 text-ink sm:text-3xl sm:leading-10 lg:text-4xl lg:leading-[1.25]">
          {activity.title}
        </h1>
        <p className="mt-4 whitespace-pre-wrap break-words text-sm leading-7 text-ink-muted">
          {activity.summary}
        </p>
        <div className="mt-5 flex min-w-0 items-start gap-2 text-sm text-ink">
          <Building2 aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-campus-green" />
          <span className="min-w-0 break-words font-semibold">{activity.organizer}</span>
        </div>
        {activity.responsible_people.length > 0 && (
          <p className="mt-2 text-xs leading-6 text-ink-muted">
            负责人：{activity.responsible_people.map((person) => person.nickname).join('、')}
          </p>
        )}
      </div>

      <div data-testid="activity-detail-media" className="aspect-[16/9] min-w-0 overflow-hidden rounded-card bg-[#E9EEF1]">
        {showCover ? (
          <img
            src={activity.cover_url ?? undefined}
            alt={`${activity.title}封面`}
            onError={() => setFailedCoverUrl(activity.cover_url)}
            className="size-full object-cover"
          />
        ) : (
          <span role="img" aria-label="活动封面占位图" className="flex size-full items-center justify-center text-campus-green">
            <Image aria-hidden="true" className="size-12" />
          </span>
        )}
      </div>
    </header>
  )
}
