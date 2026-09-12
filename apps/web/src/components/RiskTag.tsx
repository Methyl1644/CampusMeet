import { RISK_TAG } from '@shared/constants'
import type { RiskLevel } from '@shared/types'
import { CircleAlert, CircleCheck, ShieldAlert } from 'lucide-react'

const riskStyles = {
  low: {
    icon: CircleCheck,
    className: 'border-campus-green/25 bg-green-50 text-campus-green',
  },
  medium: {
    icon: CircleAlert,
    className: 'border-campus-gold/30 bg-amber-50 text-amber-800',
  },
  high: {
    icon: ShieldAlert,
    className: 'border-red-200 bg-red-50 text-red-700',
  },
} satisfies Record<
  RiskLevel,
  { icon: typeof CircleCheck; className: string }
>

export default function RiskTag({ level }: { level: RiskLevel }) {
  const config = RISK_TAG[level]
  const style = riskStyles[level]
  const Icon = style.icon

  return (
    <span
      aria-label={`风险等级：${config.label}`}
      className={`inline-flex min-h-6 items-center gap-1 whitespace-nowrap rounded-card border px-2 py-0.5 text-xs font-medium ${style.className}`}
    >
      <Icon aria-hidden="true" className="size-3.5 shrink-0" />
      {config.label}
    </span>
  )
}
