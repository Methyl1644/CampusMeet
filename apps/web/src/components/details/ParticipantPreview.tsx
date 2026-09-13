import { UsersRound } from 'lucide-react'
import type { ExploreUserSummary } from '@shared/types'

export default function ParticipantPreview({
  people,
  total,
  title = '参与者',
  itemLabel = '参与者',
}: {
  people: ExploreUserSummary[]
  total: number
  title?: string
  itemLabel?: string
}) {
  const preview = people.slice(0, 8)

  return (
    <section aria-labelledby="participant-preview-title" className="border-t border-stone pt-7">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <p className="section-label">共同参与</p>
          <h2 id="participant-preview-title" className="mt-2 text-xl font-bold text-ink">{title}</h2>
        </div>
        <span className="inline-flex items-center gap-1.5 text-sm text-ink-muted">
          <UsersRound aria-hidden="true" className="size-4" />共 {total} 人
        </span>
      </div>
      {preview.length > 0 ? (
        <ul className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {preview.map((person) => (
            <li key={person.id} aria-label={`${itemLabel}${person.nickname}`} className="flex min-w-0 items-center gap-3 rounded-card border border-stone bg-paper px-3 py-3">
              <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-[#EAF3F0] text-sm font-bold text-campus-green">
                {person.nickname.charAt(0) || '同'}
              </span>
              <span className="min-w-0">
                <span className="block truncate text-sm font-semibold text-ink">{person.nickname}</span>
                <span className="mt-0.5 block truncate text-xs text-ink-muted">{[person.major, person.grade].filter(Boolean).join(' · ') || '校园伙伴'}</span>
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-4 border-y border-stone py-6 text-sm text-ink-muted">暂时还没有可展示的{title}</p>
      )}
    </section>
  )
}
