import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { ArrowRight, ChevronLeft, ChevronRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { RecommendedHomeTopic } from '@shared/types'
import HomeEventCard from './HomeEventCard'

interface RecommendationRailProps {
  topics: RecommendedHomeTopic[]
  degraded?: boolean
}

function prefersReducedMotion() {
  return typeof window !== 'undefined'
    && typeof window.matchMedia === 'function'
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

export default function RecommendationRail({ topics, degraded = false }: RecommendationRailProps) {
  const railRef = useRef<HTMLUListElement>(null)
  const [atStart, setAtStart] = useState(true)
  const [atEnd, setAtEnd] = useState(true)

  const updateBoundaries = useCallback(() => {
    const rail = railRef.current
    if (!rail) return

    const maximum = Math.max(0, rail.scrollWidth - rail.clientWidth)
    setAtStart(rail.scrollLeft <= 1)
    setAtEnd(maximum <= 1 || rail.scrollLeft >= maximum - 1)
  }, [])

  useLayoutEffect(() => {
    updateBoundaries()
  }, [topics, updateBoundaries])

  useEffect(() => {
    const rail = railRef.current
    if (!rail || typeof ResizeObserver === 'undefined') {
      window.addEventListener('resize', updateBoundaries)
      return () => window.removeEventListener('resize', updateBoundaries)
    }

    const observer = new ResizeObserver(updateBoundaries)
    observer.observe(rail)
    return () => observer.disconnect()
  }, [updateBoundaries])

  const moveRail = (direction: -1 | 1) => {
    const rail = railRef.current
    if (!rail) return

    const maximum = Math.max(0, rail.scrollWidth - rail.clientWidth)
    const nextLeft = Math.min(maximum, Math.max(0, rail.scrollLeft + direction * rail.clientWidth * 0.9))
    rail.scrollTo({
      left: nextLeft,
      behavior: prefersReducedMotion() ? 'auto' : 'smooth',
    })
  }

  return (
    <section aria-labelledby="home-recommendations-title" className="min-w-0 overflow-hidden">
      <div className="flex min-h-10 items-center justify-between gap-4">
        <div className="min-w-0">
          <h1 id="home-recommendations-title" className="text-2xl font-bold text-ink sm:text-[28px]">
            为你推荐
          </h1>
          <p className="mt-1 text-sm text-ink-muted">结合你的兴趣与近期校园安排</p>
        </div>

        {topics.length > 0 ? (
          <div role="group" className="hidden shrink-0 items-center gap-1 md:flex" aria-label="推荐活动翻页">
            <button
              type="button"
              aria-label="查看前面的推荐"
              aria-hidden={atStart}
              title="查看前面的推荐"
              disabled={atStart}
              onClick={() => moveRail(-1)}
              className={`icon-button border border-stone bg-paper transition-opacity duration-feedback ${atStart ? 'invisible pointer-events-none' : ''}`}
            >
              <ChevronLeft aria-hidden="true" className="size-5" />
            </button>
            <button
              type="button"
              aria-label="查看后续推荐"
              aria-hidden={atEnd}
              title="查看后续推荐"
              disabled={atEnd}
              onClick={() => moveRail(1)}
              className={`icon-button border border-stone bg-paper transition-opacity duration-feedback ${atEnd ? 'invisible pointer-events-none' : ''}`}
            >
              <ChevronRight aria-hidden="true" className="size-5" />
            </button>
          </div>
        ) : null}
      </div>

      {degraded ? (
        <div role="status" className="mt-5 border-y border-stone py-8 text-sm text-ink-muted">
          推荐活动暂时无法加载
        </div>
      ) : topics.length > 0 ? (
        <ul
          ref={railRef}
          aria-label="推荐活动"
          onScroll={updateBoundaries}
          className="mt-5 flex min-w-0 snap-x snap-mandatory gap-4 overflow-x-auto pb-3 pr-1"
        >
          {topics.map((topic) => (
            <li key={topic.id} className="shrink-0 snap-start">
              <HomeEventCard topic={topic} />
            </li>
          ))}
        </ul>
      ) : (
        <div className="mt-5 flex min-h-32 items-center justify-between gap-4 border-y border-stone py-6">
          <p className="text-sm text-ink-muted">暂时没有新的活动推荐</p>
          <Link
            to="/discover?view=events"
            className="inline-flex shrink-0 items-center gap-1 text-sm font-semibold text-primary-700 transition-colors duration-feedback hover:text-primary-800"
          >
            探索活动
            <ArrowRight aria-hidden="true" className="size-4" />
          </Link>
        </div>
      )}
    </section>
  )
}
