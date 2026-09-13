import { useRef } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import type { ExploreView } from '@/features/explore/exploreState'

interface CategoryRailProps {
  view: ExploreView
  selectedTagIds: string[]
  onChange: (tagIds: string[]) => void
}

const categories = [
  { id: 'activity_ai', label: '人工智能' },
  { id: 'activity_innovation', label: '创新创业' },
  { id: 'activity_programming', label: '程序设计' },
  { id: 'activity_robotics', label: '机器人' },
  { id: 'activity_math_modeling', label: '数学建模' },
  { id: 'activity_volunteering', label: '志愿服务' },
  { id: 'activity_badminton', label: '羽毛球' },
  { id: 'activity_photography', label: '摄影' },
] as const

const categoryOrder = new Map<string, number>(categories.map((item, index) => [item.id, index]))

export default function CategoryRail({ view, selectedTagIds, onChange }: CategoryRailProps) {
  const rail = useRef<HTMLDivElement>(null)
  const selected = new Set(selectedTagIds)

  const toggle = (id: string) => {
    const next = selected.has(id)
      ? selectedTagIds.filter((tagId) => tagId !== id)
      : [...selectedTagIds, id]
    onChange([...new Set(next)].sort((left, right) => (
      (categoryOrder.get(left) ?? Number.MAX_SAFE_INTEGER)
      - (categoryOrder.get(right) ?? Number.MAX_SAFE_INTEGER)
    )))
  }

  const move = (direction: -1 | 1) => {
    const element = rail.current
    if (!element) return
    const maximum = Math.max(0, element.scrollWidth - element.clientWidth)
    const left = Math.min(maximum, Math.max(
      0,
      element.scrollLeft + direction * element.clientWidth * 0.9,
    ))
    const reducedMotion = typeof window.matchMedia === 'function'
      && window.matchMedia('(prefers-reduced-motion: reduce)').matches
    element.scrollTo({ left, behavior: reducedMotion ? 'auto' : 'smooth' })
  }

  return (
    <section aria-label="兴趣分类" className="relative mt-4 min-w-0 border-y border-stone py-3">
      <div
        ref={rail}
        className="flex min-w-0 gap-2 overflow-x-auto px-0.5 pb-1 pr-20 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden md:pr-24"
      >
        <button
          type="button"
          aria-pressed={selectedTagIds.length === 0}
          onClick={() => onChange([])}
          className={`min-h-9 shrink-0 rounded-full border px-3 text-sm font-medium transition-colors duration-feedback ${selectedTagIds.length === 0 ? 'border-primary-600 bg-primary-600 text-white' : 'border-stone bg-paper text-ink hover:border-primary-300 hover:text-primary-700'}`}
        >
          全部
        </button>
        {categories.map((category) => {
          const active = selected.has(category.id)
          return (
            <button
              key={category.id}
              type="button"
              aria-pressed={active}
              onClick={() => toggle(category.id)}
              className={`min-h-9 shrink-0 rounded-full border px-3 text-sm font-medium transition-colors duration-feedback ${active ? 'border-primary-600 bg-primary-50 text-primary-700' : 'border-stone bg-paper text-ink hover:border-primary-300 hover:text-primary-700'}`}
            >
              {category.label}
            </button>
          )
        })}
      </div>
      <div className="absolute right-0 top-2 hidden h-11 items-center gap-1 bg-[#F8F8FA] pl-3 md:flex">
        <button
          type="button"
          className="icon-button size-9 border border-stone bg-paper"
          aria-label="向左浏览分类"
          title="向左浏览分类"
          onClick={() => move(-1)}
        >
          <ChevronLeft aria-hidden="true" className="size-4" />
        </button>
        <button
          type="button"
          className="icon-button size-9 border border-stone bg-paper"
          aria-label="向右浏览分类"
          title="向右浏览分类"
          onClick={() => move(1)}
        >
          <ChevronRight aria-hidden="true" className="size-4" />
        </button>
      </div>
      <span className="sr-only">当前浏览{view === 'activity' ? '活动' : '组队'}分类</span>
    </section>
  )
}
