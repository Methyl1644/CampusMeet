import { SOURCE_BADGE } from '@shared/constants'
import type { SourceType } from '@shared/types'

export default function SourceBadge({ type }: { type: SourceType }) {
  const config = SOURCE_BADGE[type]
  return <span className={`badge ${config.color}`}>{config.label}</span>
}
