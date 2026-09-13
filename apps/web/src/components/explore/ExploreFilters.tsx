import { useEffect, useRef, useState, type ReactNode } from 'react'
import { RotateCcw, SlidersHorizontal, X } from 'lucide-react'
import type {
  ActivityExploreState,
  ExploreView,
  ExploreViewStateUpdate,
  GroupExploreState,
} from '@/features/explore/exploreState'

interface ExploreFiltersProps {
  view: ExploreView
  state: ActivityExploreState | GroupExploreState
  onChange: (update: ExploreViewStateUpdate) => void
}

interface FilterFieldsProps extends ExploreFiltersProps {
  idPrefix: string
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return <label className="grid min-w-0 gap-1 text-xs font-medium text-ink-muted">{label}{children}</label>
}

function FilterFields({ view, state, onChange, idPrefix }: FilterFieldsProps) {
  const noun = view === 'activity' ? '活动' : '组队'
  const updateFilter = (name: 'date' | 'status' | 'type' | 'campus', value: string) => {
    onChange({ filters: { [name]: value } })
  }

  return (
    <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-4">
      <Field label={`${noun}日期`}>
        <select id={`${idPrefix}-date`} aria-label={`${noun}日期`} value={state.filters.date} onChange={(event) => updateFilter('date', event.target.value)} className="input-base h-10 bg-paper py-1">
          <option value="">全部日期</option>
          <option value="upcoming">即将开始</option>
          {view === 'activity' && <option value="registration_open">报名中</option>}
          <option value="past">往期内容</option>
        </select>
      </Field>
      <Field label={`${noun}状态`}>
        <select id={`${idPrefix}-status`} aria-label={`${noun}状态`} value={state.filters.status} onChange={(event) => updateFilter('status', event.target.value)} className="input-base h-10 bg-paper py-1">
          <option value="">全部状态</option>
          {view === 'activity' ? <><option value="registration_open">开放报名</option><option value="ended">已结束</option></> : <><option value="recruiting">招募中</option><option value="full">已满员</option><option value="closed">已关闭</option></>}
        </select>
      </Field>
      <Field label={`${noun}类型`}>
        <select id={`${idPrefix}-type`} aria-label={`${noun}类型`} value={state.filters.type} onChange={(event) => updateFilter('type', event.target.value)} className="input-base h-10 bg-paper py-1">
          <option value="">全部类型</option>
          {view === 'activity' ? <><option value="official">官方活动</option><option value="organization">组织活动</option><option value="open_team">可发起组队</option><option value="official_signup">官方报名</option><option value="information_only">仅供浏览</option></> : <><option value="team_recruitment">招募队友</option><option value="official_signup">官方报名</option><option value="discussion">讨论交流</option><option value="casual_invitation">同学自发</option></>}
        </select>
      </Field>
      <Field label={`${noun}校区`}>
        <select id={`${idPrefix}-campus`} aria-label={`${noun}校区`} value={state.filters.campus} onChange={(event) => updateFilter('campus', event.target.value)} className="input-base h-10 bg-paper py-1">
          <option value="">全部校区</option>
          <option value="仙林校区">仙林校区</option>
          <option value="鼓楼校区">鼓楼校区</option>
          <option value="浦口校区">浦口校区</option>
          <option value="苏州校区">苏州校区</option>
        </select>
      </Field>
    </div>
  )
}

export default function ExploreFilters(props: ExploreFiltersProps) {
  const [open, setOpen] = useState(false)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const closeRef = useRef<HTMLButtonElement>(null)
  const dialogRef = useRef<HTMLDivElement>(null)
  const activeCount = Object.values(props.state.filters).filter(Boolean).length
  const noun = props.view === 'activity' ? '活动' : '组队'

  const close = () => {
    setOpen(false)
    window.setTimeout(() => triggerRef.current?.focus(), 0)
  }

  useEffect(() => {
    if (!open) return
    closeRef.current?.focus()
    const handleKeyDown = (event: globalThis.KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        close()
        return
      }
      if (event.key !== 'Tab') return
      const focusable = Array.from(dialogRef.current?.querySelectorAll<HTMLElement>('button:not([disabled]), select:not([disabled])') ?? [])
      if (focusable.length === 0) return
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [open])

  const clearFilters = () => props.onChange({ filters: { date: '', status: '', type: '', campus: '' } })

  return (
    <section aria-label="探索筛选" className="mt-4">
      <div className="flex items-center justify-between gap-3 md:hidden">
        <button ref={triggerRef} type="button" onClick={() => setOpen(true)} className="btn-secondary min-h-10" aria-label="打开筛选">
          <SlidersHorizontal aria-hidden="true" className="size-4" />
          <span>筛选{activeCount > 0 ? ` (${activeCount})` : ''}</span>
        </button>
        {activeCount > 0 && <button type="button" onClick={clearFilters} className="inline-flex min-h-10 items-center gap-1 text-sm font-semibold text-primary-700"><RotateCcw aria-hidden="true" className="size-4" />重置</button>}
      </div>
      <div className="hidden md:block">
        <FilterFields {...props} idPrefix="desktop-filter" />
      </div>

      {open && (
        <div className="fixed inset-0 z-50 flex items-end bg-black/35 md:hidden" onMouseDown={(event) => { if (event.currentTarget === event.target) close() }}>
          <div ref={dialogRef} role="dialog" aria-modal="true" aria-labelledby="explore-filter-title" className="max-h-[82dvh] w-full overflow-y-auto rounded-t-[12px] bg-paper px-4 pb-[calc(1rem+env(safe-area-inset-bottom))] pt-4 shadow-xl">
            <div className="mb-4 flex items-center justify-between gap-4">
              <h2 id="explore-filter-title" className="text-lg font-bold text-ink">筛选{noun}</h2>
              <button ref={closeRef} type="button" onClick={close} className="icon-button" aria-label="关闭筛选" title="关闭筛选"><X aria-hidden="true" className="size-5" /></button>
            </div>
            <FilterFields {...props} idPrefix="mobile-filter" />
            <div className="mt-5 flex gap-3 border-t border-stone pt-4">
              <button type="button" onClick={clearFilters} className="btn-secondary flex-1"><RotateCcw aria-hidden="true" className="size-4" />重置</button>
              <button type="button" onClick={close} className="btn-primary flex-1">查看结果</button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
