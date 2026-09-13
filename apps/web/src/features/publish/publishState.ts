import type { PostDraft, FieldStatus, PostPurpose, StandardTag } from '@shared/types'

export interface PublishContext {
  kind: 'casual_invitation' | 'topic_team'
  topic_id: string | null
  activity: { id: string; title: string; cover_url: string | null } | null
  allowed_purposes: PostPurpose[]
  default_purpose: PostPurpose
  permission_explanations: Record<string, string>
  inherited_tags: StandardTag[]
  defaults: Partial<PostDraft>
  revision: string
  max_members: number
}
export type FieldStates = Record<string, { value: unknown; status: FieldStatus }>
export type PublishPhase = 'conversation' | 'thinking' | 'review' | 'publishing' | 'published'
export const emptyDraft: PostDraft = { activity_name: '', target_members: 0, needed_roles: [], weekly_hours: '', school_scope: '', deadline: '', description: '' }
export const purposeLabels: Record<PostPurpose, string> = { team_recruitment: '招募队友', official_signup: '官方报名', discussion: '经验交流' }
export const fieldLabels: Record<string, string> = { activity_name: '活动名称', target_members: '总人数（包含自己）', needed_roles: '期待的角色或能力', weekly_hours: '时间安排', school_scope: '校区或地点', deadline: '截止时间', description: '介绍与参与说明' }
const unknownText = new Set(['未知', '待定', '暂不确定', '不知道', '不确定', '暂无', '跳过', '先跳过', '待商定', '无', '没有'])

export function requiredFields(context: PublishContext, purpose: PostPurpose): (keyof PostDraft)[] {
  if (purpose === 'discussion') return ['activity_name', 'description']
  if (purpose === 'official_signup') return ['activity_name', 'target_members', 'deadline', 'description']
  return ['activity_name', 'target_members', 'needed_roles', 'weekly_hours', 'school_scope', ...(context.kind === 'topic_team' ? ['deadline' as const] : [])]
}

export function missingFields(draft: PostDraft, states: FieldStates, context: PublishContext, purpose: PostPurpose) {
  return requiredFields(context, purpose).filter((field) => {
    const value = draft[field]
    const status = states[field]?.status
    if (status === 'pending' || status === 'unknown' || status === 'skipped') return true
    if (field === 'target_members') return !Number.isInteger(value) || Number(value) < 1 || Number(value) > (purpose === 'official_signup' ? context.max_members : 100)
    if (field === 'needed_roles') return !Array.isArray(value) || (!value.length && status !== 'none') || value.some((role) => !role.trim() || unknownText.has(role.trim()))
    return typeof value !== 'string' || !value.trim() || unknownText.has(value.trim())
  })
}

export function completeness(draft: PostDraft, states: FieldStates, context: PublishContext, purpose: PostPurpose) {
  return 1 - missingFields(draft, states, context, purpose).length / requiredFields(context, purpose).length
}

export function normalizeDraft(value: Partial<PostDraft>): PostDraft {
  return {
    activity_name: typeof value.activity_name === 'string' ? value.activity_name : '',
    description: typeof value.description === 'string' ? value.description : '',
    target_members: typeof value.target_members === 'number' ? value.target_members : 0,
    needed_roles: Array.isArray(value.needed_roles) ? value.needed_roles.filter((role) => typeof role === 'string') : [],
    weekly_hours: typeof value.weekly_hours === 'string' ? value.weekly_hours : '',
    school_scope: typeof value.school_scope === 'string' ? value.school_scope : '',
    deadline: typeof value.deadline === 'string' ? value.deadline : '',
  }
}

export function requestError(error: unknown, fallback: string): string {
  const value = error as { response?: { data?: { detail?: unknown; message?: string } }; code?: string }
  const detail = value.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (detail && typeof detail === 'object' && 'message' in detail) return String(detail.message)
  if (Array.isArray(detail) && detail[0]?.loc) return `请检查${fieldLabels[detail[0].loc.at(-1)] || '填写内容'}的格式或长度。`
  if (value.code === 'ECONNABORTED') return '等待超时，你的内容已保留。可以重试或手动完善。'
  if (error instanceof Error && /[\u4e00-\u9fff]/.test(error.message)) return error.message
  return value.response?.data?.message || fallback
}
