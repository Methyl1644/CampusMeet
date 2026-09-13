import { useRef, type KeyboardEvent } from 'react'
import { CalendarDays, UsersRound } from 'lucide-react'
import { motion, useReducedMotion } from 'motion/react'
import type { ExploreView } from '@/features/explore/exploreState'

interface ExploreSwitcherProps {
  view: ExploreView
  onChange: (view: ExploreView) => void
}

const views = [
  { id: 'activity', label: '活动', icon: CalendarDays },
  { id: 'group', label: '组队', icon: UsersRound },
] as const

export default function ExploreSwitcher({ view, onChange }: ExploreSwitcherProps) {
  const shouldReduceMotion = useReducedMotion()
  const tabs = useRef<Partial<Record<ExploreView, HTMLButtonElement>>>({})

  const selectFromKeyboard = (event: KeyboardEvent<HTMLButtonElement>, current: ExploreView) => {
    const currentIndex = views.findIndex((item) => item.id === current)
    let nextIndex: number | null = null
    if (event.key === 'ArrowRight') nextIndex = (currentIndex + 1) % views.length
    if (event.key === 'ArrowLeft') nextIndex = (currentIndex - 1 + views.length) % views.length
    if (event.key === 'Home') nextIndex = 0
    if (event.key === 'End') nextIndex = views.length - 1
    if (nextIndex === null) return

    event.preventDefault()
    const next = views[nextIndex].id
    onChange(next)
    tabs.current[next]?.focus()
  }

  return (
    <div
      role="tablist"
      aria-label="探索分类"
      className="relative grid h-11 w-full max-w-[280px] grid-cols-2 rounded-card border border-stone bg-[#EEF0F3] p-1"
    >
      {views.map(({ id, label, icon: Icon }) => {
        const selected = id === view
        return (
          <button
            key={id}
            ref={(element) => { tabs.current[id] = element ?? undefined }}
            id={`explore-${id}-tab`}
            type="button"
            role="tab"
            aria-selected={selected}
            aria-controls="explore-results"
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(id)}
            onKeyDown={(event) => selectFromKeyboard(event, id)}
            className={`relative z-10 inline-flex min-w-0 items-center justify-center gap-1.5 rounded-[6px] px-3 text-sm font-semibold transition-colors duration-feedback ${selected ? 'text-primary-700' : 'text-ink-muted hover:text-ink'}`}
          >
            {selected && (
              <motion.span
                layoutId="explore-selected-view"
                className="absolute inset-0 -z-10 rounded-[6px] bg-paper shadow-panel"
                transition={{ duration: shouldReduceMotion ? 0.1 : 0.22, ease: [0.22, 1, 0.36, 1] }}
              />
            )}
            <Icon aria-hidden="true" className="size-4 shrink-0" />
            {label}
          </button>
        )
      })}
    </div>
  )
}
