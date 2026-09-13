import { CalendarDays, Clock3, MapPin, UsersRound } from 'lucide-react'
import type { ExploreActivityDetail } from '@shared/types'

function formatDate(value: string | null, fallback: string) {
  if (!value) return fallback
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return fallback
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric', month: 'long', day: 'numeric', weekday: 'short',
    hour: '2-digit', minute: '2-digit', hour12: false,
  }).format(date)
}

export default function ActivityFacts({ activity }: { activity: ExploreActivityDetail }) {
  const capacity = activity.capacity === null ? '人数不限' : `${activity.capacity} 人`
  const activityTime = activity.activity_end_at
    ? `${formatDate(activity.activity_start_at, '待公布')} 至 ${formatDate(activity.activity_end_at, '待公布')}`
    : formatDate(activity.activity_start_at, '待公布')
  const facts = [
    { icon: CalendarDays, label: '活动时间', value: activityTime },
    { icon: Clock3, label: '报名截止', value: formatDate(activity.registration_deadline, '待公布') },
    { icon: MapPin, label: '地点与校区', value: [activity.location_name, activity.campus_scope].filter(Boolean).join(' · ') || '待公布' },
    { icon: UsersRound, label: '人数上限', value: capacity },
  ]

  return (
    <section aria-label="活动关键信息" className="mt-6 border-y border-stone bg-paper">
      <dl className="grid sm:grid-cols-2 lg:grid-cols-4">
        {facts.map(({ icon: Icon, label, value }) => (
          <div key={label} className="flex min-w-0 gap-3 border-b border-stone px-4 py-4 last:border-b-0 sm:[&:nth-last-child(-n+2)]:border-b-0 lg:border-b-0 lg:border-r lg:last:border-r-0">
            <Icon aria-hidden="true" className="mt-0.5 size-[18px] shrink-0 text-campus-green" />
            <div className="min-w-0">
              <dt className="text-xs text-ink-muted">{label}</dt>
              <dd className="mt-1 break-words text-sm font-semibold leading-6 text-ink">{value}</dd>
            </div>
          </div>
        ))}
      </dl>
    </section>
  )
}
