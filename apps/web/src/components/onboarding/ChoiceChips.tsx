import { Minus, Plus } from 'lucide-react'

interface ChoiceChipsProps {
  label: string
  options: readonly string[]
  selected: string[]
  onChange: (nextSelected: string[]) => void
}

export default function ChoiceChips({
  label,
  options,
  selected,
  onChange,
}: ChoiceChipsProps) {
  const selectedSet = new Set(selected)

  const toggle = (option: string) => {
    if (selectedSet.has(option)) {
      onChange(selected.filter((item) => item !== option))
      return
    }
    onChange([...selected, option])
  }

  return (
    <div role="group" aria-label={label} className="flex flex-wrap gap-2.5">
      {options.map((option) => {
        const isSelected = selectedSet.has(option)
        const Icon = isSelected ? Minus : Plus
        return (
          <button
            key={option}
            type="button"
            aria-pressed={isSelected}
            onClick={() => toggle(option)}
            className="onboarding-choice"
          >
            <span>{option}</span>
            <Icon aria-hidden="true" className="size-4 shrink-0" />
          </button>
        )
      })}
    </div>
  )
}
