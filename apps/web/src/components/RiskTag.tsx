import { RISK_TAG } from '@shared/constants'
import type { RiskLevel } from '@shared/types'

export default function RiskTag({ level }: { level: RiskLevel }) {
  const config = RISK_TAG[level]
  return <span className={`badge ${config.color}`}>{config.label}</span>
}
