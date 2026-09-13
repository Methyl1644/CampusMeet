import { useId, useRef, useState, type KeyboardEvent } from 'react'
import { ArrowRight, CalendarDays, Image } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { HomeTopic } from '@shared/types'

type EventTab = 'attending' | 'saved'

interface MyEventsSummaryProps {
  attending: HomeTopic[]
  saved: HomeTopic[]
  attendingDegraded?: boolean
  savedDegraded?: boolean
}

const tabOrder: EventTab[] = ['attending', 'saved']
const tabLabels: Record<EventTab, string> = {
  attending: '参加中',
  saved: '已收藏',
}

function eventDate(topic: HomeTopic) {
  if (!topic.activity_start_at) return '时间待公布'

  return new Intl.DateTimeFormat('zh-CN', {
    month: 'long',
    day: 'numeric',
    weekday: 'short',
  }).format(new Date(topic.activity_start_at))
}

export default function MyEventsSummary({
  attending,
  saved,
  attendingDegraded = false,
  savedDegraded = false,
}: MyEventsSummaryProps) {
  const [activeTab, setActiveTab] = useState<EventTab>('attending')
  const id = useId()
  const tabRefs = useRef<Partial<Record<EventTab, HTMLButtonElement>>>({})
  const eventsByTab: Record<EventTab, HomeTopic[]> = { attending, saved }
  const degradedByTab: Record<EventTab, boolean> = {
    attending: attendingDegraded,
    saved: savedDegraded,
  }

  const selectFromKeyboard = (event: KeyboardEvent<HTMLButtonElement>, current: EventTab) => {
    const currentIndex = tabOrder.indexOf(current)
    let nextTab: EventTab | null = null

    if (event.key === 'ArrowRight') nextTab = tabOrder[(currentIndex + 1) % tabOrder.length]
    if (event.key === 'ArrowLeft') nextTab = tabOrder[(currentIndex - 1 + tabOrder.length) % tabOrder.length]
    if (event.key === 'Home') nextTab = tabOrder[0]
    if (event.key === 'End') nextTab = tabOrder[tabOrder.length - 1]
    if (!nextTab) return

    event.preventDefault()
    setActiveTab(nextTab)
    tabRefs.current[nextTab]?.focus()
  }

  return (
    <section aria-labelledby={`${id}-title`} className="overflow-hidden rounded-card border border-stone bg-paper shadow-panel">
      <div className="flex items-center justify-between gap-3 px-4 pt-4">
        <h2 id={`${id}-title`} className="text-base font-semibold text-ink">
          我的活动
        </h2>
        <Link
          to="/my/activities"
          className="inline-flex items-center gap-1 text-xs font-semibold text-primary-700 transition-colors duration-fast hover:text-primary-800"
        >
          查看全部活动
          <ArrowRight aria-hidden="true" className="size-3.5" />
        </Link>
      </div>

      <div role="tablist" aria-label="我的活动分类" className="mt-2 flex border-b border-stone px-4">
        {tabOrder.map((tab) => {
          const selected = activeTab === tab
          return (
            <button
              key={tab}
              ref={(element) => {
                tabRefs.current[tab] = element ?? undefined
              }}
              id={`${id}-${tab}-tab`}
              type="button"
              role="tab"
              aria-selected={selected}
              aria-controls={`${id}-${tab}-panel`}
              tabIndex={selected ? 0 : -1}
              onClick={() => setActiveTab(tab)}
              onKeyDown={(event) => selectFromKeyboard(event, tab)}
              className={`min-h-10 flex-1 border-b-2 px-2 py-2 text-sm font-semibold transition-colors duration-fast ${
                selected
                  ? 'border-primary-600 text-primary-700'
                  : 'border-transparent text-ink-muted hover:text-primary-700'
              }`}
            >
              {tabLabels[tab]}
            </button>
          )
        })}
      </div>

      {tabOrder.map((tab) => (
        <EventTabPanel
          key={tab}
          id={`${id}-${tab}-panel`}
          labelledBy={`${id}-${tab}-tab`}
          topic={eventsByTab[tab][0]}
          degradedMessage={
            degradedByTab[tab] ? `${tabLabels[tab]}的活动暂时无法加载` : undefined
          }
          emptyMessage={tab === 'attending' ? '还没有参加的活动' : '还没有收藏的活动'}
          hidden={activeTab !== tab}
        />
      ))}
    </section>
  )
}

function EventTabPanel({
  id,
  labelledBy,
  topic,
  degradedMessage,
  emptyMessage,
  hidden,
}: {
  id: string
  labelledBy: string
  topic: HomeTopic | undefined
  degradedMessage: string | undefined
  emptyMessage: string
  hidden: boolean
}) {
  return (
    <div
      id={id}
      role="tabpanel"
      aria-labelledby={labelledBy}
      tabIndex={0}
      hidden={hidden}
      style={{ minHeight: '8.5rem' }}
      className="items-center px-4 py-3 [&:not([hidden])]:flex"
    >
      {!hidden && degradedMessage ? (
        <p role="status" className="text-sm text-ink-muted">
          {degradedMessage}
        </p>
      ) : !hidden && topic ? (
        <Link to={`/topics/${topic.id}`} className="group flex min-w-0 flex-1 items-center gap-3">
          {topic.cover_url ? (
            <img
              src={topic.cover_url}
              alt=""
              className="h-[72px] w-[84px] shrink-0 rounded-[12px] object-cover"
            />
          ) : (
            <span className="flex h-[72px] w-[84px] shrink-0 items-center justify-center rounded-[12px] bg-[#F3F2F6] text-primary-500">
              <Image aria-hidden="true" className="size-6" />
            </span>
          )}
          <span className="min-w-0 flex-1">
            <span className="flex items-center gap-1 text-xs font-semibold text-primary-700">
              <CalendarDays aria-hidden="true" className="size-3.5 shrink-0" />
              {eventDate(topic)}
            </span>
            <span className="mt-1 line-clamp-2 text-sm font-semibold leading-5 text-ink transition-colors duration-fast group-hover:text-primary-700">
              {topic.title}
            </span>
            <span className="mt-1 block truncate text-xs text-ink-muted">{topic.organizer}</span>
          </span>
        </Link>
      ) : !hidden ? (
        <div className="flex min-w-0 flex-1 items-center justify-between gap-3">
          <p className="text-sm text-ink-muted">{emptyMessage}</p>
          <Link
            to="/discover?view=activity"
            className="shrink-0 text-sm font-semibold text-primary-700 hover:text-primary-800"
          >
            探索活动
          </Link>
        </div>
      ) : null}
    </div>
  )
}
