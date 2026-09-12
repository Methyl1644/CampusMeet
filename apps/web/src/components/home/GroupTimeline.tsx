import { CheckCircle2, Circle, Clock3, UsersRound } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { HomeTimelineItem } from '@shared/types'

interface TimelineGroup {
  key: string
  label: string
  items: HomeTimelineItem[]
}

function localDateKey(value: Date) {
  return `${value.getFullYear()}-${value.getMonth() + 1}-${value.getDate()}`
}

function dateLabel(value: Date) {
  const today = new Date()
  const tomorrow = new Date(today.getFullYear(), today.getMonth(), today.getDate() + 1)
  const date = new Date(value.getFullYear(), value.getMonth(), value.getDate())

  if (date.getTime() === new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime()) {
    return '今天'
  }
  if (date.getTime() === tomorrow.getTime()) return '明天'

  return new Intl.DateTimeFormat('zh-CN', {
    month: 'long',
    day: 'numeric',
    weekday: 'short',
  }).format(value)
}

function groupTimeline(items: HomeTimelineItem[]): TimelineGroup[] {
  const groups = new Map<string, TimelineGroup>()

  for (const item of items) {
    const dueDate = item.due_at ? new Date(item.due_at) : null
    const key = dueDate ? localDateKey(dueDate) : 'undated'
    const existing = groups.get(key)
    if (existing) {
      existing.items.push(item)
    } else {
      groups.set(key, {
        key,
        label: dueDate ? dateLabel(dueDate) : '日期待定',
        items: [item],
      })
    }
  }

  return Array.from(groups.values())
}

function dueTime(value: string | null) {
  if (!value) return '时间待定'
  return new Intl.DateTimeFormat('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(new Date(value))
}

function timelineItemKey(item: HomeTimelineItem, index: number) {
  const teamKey = item.team_id.trim() || `legacy-team-${index}`
  const taskKey = item.task_id.trim() || `legacy-task-${index}`
  return JSON.stringify([teamKey, taskKey])
}

export default function GroupTimeline({
  items,
  degraded = false,
}: {
  items: HomeTimelineItem[]
  degraded?: boolean
}) {
  const groups = groupTimeline(items)

  return (
    <section aria-labelledby="home-timeline-title" className="min-w-0">
      <div>
        <h2 id="home-timeline-title" className="text-xl font-bold text-ink sm:text-2xl">
          来自我的小组
        </h2>
        <p className="mt-1 text-sm text-ink-muted">近期任务与协作安排</p>
      </div>

      {degraded ? (
        <div role="status" className="mt-5 border-y border-stone py-8 text-sm text-ink-muted">
          小组动态暂时无法加载
        </div>
      ) : groups.length > 0 ? (
        <div className="mt-5 border-y border-stone bg-paper">
          {groups.map((group) => (
            <section key={group.key} aria-labelledby={`timeline-${group.key}`}>
              <h3
                id={`timeline-${group.key}`}
                className="border-b border-stone bg-[#F5F6F8] px-4 py-2.5 text-sm font-semibold text-ink"
              >
                {group.label}
              </h3>
              <ul>
                {group.items.map((item, index) => (
                  <li key={timelineItemKey(item, index)} className="border-b border-stone last:border-b-0">
                    <Link
                      to={`/teams/${item.team_id}`}
                      className="group grid min-w-0 grid-cols-[minmax(0,1fr)_auto] items-center gap-4 px-4 py-4 transition-colors duration-feedback hover:bg-primary-50"
                    >
                      <span className="min-w-0">
                        <span className="flex items-center gap-1.5 truncate text-xs font-medium text-ink-muted">
                          <UsersRound aria-hidden="true" className="size-3.5 shrink-0" />
                          {item.team_name}
                        </span>
                        <span className={`mt-1 block text-sm font-semibold leading-5 ${item.done ? 'text-ink-muted line-through' : 'text-ink'}`}>
                          {item.title}
                        </span>
                      </span>
                      <span className="flex min-w-[78px] flex-col items-end gap-1 text-xs">
                        <span className="flex items-center gap-1 text-ink-muted">
                          <Clock3 aria-hidden="true" className="size-3.5" />
                          {dueTime(item.due_at)}
                        </span>
                        <span className={`flex items-center gap-1 font-medium ${item.done ? 'text-campus-green' : 'text-primary-700'}`}>
                          {item.done ? (
                            <CheckCircle2 aria-hidden="true" className="size-3.5" />
                          ) : (
                            <Circle aria-hidden="true" className="size-3.5" />
                          )}
                          {item.done ? '已完成' : '待完成'}
                        </span>
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      ) : (
        <div className="mt-5 flex min-h-32 flex-wrap items-center justify-between gap-4 border-y border-stone py-6">
          <p className="text-sm text-ink-muted">小组有新任务时，会在这里按日期出现。</p>
          <Link
            to="/discover?view=groups"
            className="text-sm font-semibold text-primary-700 transition-colors duration-feedback hover:text-primary-800"
          >
            探索组队
          </Link>
        </div>
      )}
    </section>
  )
}
