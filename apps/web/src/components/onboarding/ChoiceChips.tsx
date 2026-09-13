import { Minus, Plus } from 'lucide-react'

interface ChoiceChipsProps {
  label: string
  options: readonly string[]
  selected: string[]
  onChange: (nextSelected: string[]) => void
  maxSelected?: number
}

export default function ChoiceChips({
  label,
  options,
  selected,
  onChange,
  maxSelected,
}: ChoiceChipsProps) {
  const selectedSet = new Set(selected)
  const atLimit = maxSelected !== undefined && selectedSet.size >= maxSelected

  const toggle = (option: string) => {
    if (selectedSet.has(option)) {
      onChange(selected.filter((item) => item !== option))
      return
    }
    if (atLimit) return
    onChange([...selected, option])
  }

  return (
    <div role="group" aria-label={label} className="flex flex-wrap gap-2.5">
      {options.map((option) => {
        const isSelected = selectedSet.has(option)
        const isDisabled = atLimit && !isSelected
        const Icon = isSelected ? Minus : Plus
        return (
          <button
            key={option}
            type="button"
            aria-pressed={isSelected}
            disabled={isDisabled}
            onClick={() => toggle(option)}
            className="onboarding-choice disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:border-stone disabled:hover:bg-paper disabled:active:scale-100"
          >
            <span>{option}</span>
            <Icon aria-hidden="true" className="size-4 shrink-0" />
          </button>
        )
      })}
      {atLimit && (
        <p role="status" aria-live="polite" className="basis-full text-sm text-ink-muted">
          最多选择 {maxSelected} 项，取消已选项后可继续选择
        </p>
      )}
    </div>
  )
}
