import type { KeyboardEvent } from 'react'

export interface CollectionTab<T extends string> {
  value: T
  label: string
}

export default function CollectionTabs<T extends string>({
  label,
  tabs,
  value,
  onChange,
}: {
  label: string
  tabs: CollectionTab<T>[]
  value: T
  onChange: (value: T) => void
}) {
  const move = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return
    event.preventDefault()
    const next = event.key === 'Home'
      ? 0
      : event.key === 'End'
        ? tabs.length - 1
        : (index + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length
    onChange(tabs[next].value)
    document.getElementById(`${label}-${tabs[next].value}`)?.focus()
  }

  return (
    <div role="tablist" aria-label={label} className="flex min-w-0 gap-2 overflow-x-auto border-b border-stone pb-3">
      {tabs.map((tab, index) => {
        const selected = tab.value === value
        return (
          <button
            key={tab.value}
            id={`${label}-${tab.value}`}
            type="button"
            role="tab"
            aria-selected={selected}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(tab.value)}
            onKeyDown={(event) => move(event, index)}
            className={`min-h-10 shrink-0 rounded-full px-5 text-sm font-bold transition-colors ${selected ? 'bg-primary-700 text-white' : 'bg-[#ECECEF] text-ink hover:bg-primary-100'}`}
          >
            {tab.label}
          </button>
        )
      })}
    </div>
  )
}
