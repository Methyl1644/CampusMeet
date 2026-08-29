import { POST_STATUS } from '@shared/constants'
import type { PostStatus } from '@shared/types'

export default function StatusBadge({ status }: { status: PostStatus }) {
  const config = POST_STATUS[status]
  return <span className={`badge ${config.color}`}>{config.label}</span>
}
