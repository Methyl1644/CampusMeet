import { post } from './client'
import { API_PATHS } from '@shared/constants'
import type {
  AgendaItem,
  DivisionItem,
  MatchResponse,
  Post,
  PostDraftRequest,
  PostDraftResponse,
  TaskItem,
} from '@shared/types'

/** AI 对话式发帖 — 发送消息获取草稿/追问 */
export function postDraft(data: PostDraftRequest) {
  return post<PostDraftResponse>(API_PATHS.agent.postDraft, data)
}

/** AI 分类与审核 */
export function classifyReview(postData: Partial<Post>) {
  return post<{
    main_category: string
    tags: string[]
    risk_level: string
    suggestions?: string[]
  }>(API_PATHS.agent.classify, postData)
}

/** AI 智能匹配 */
export function matchPosts(postId: string) {
  return post<MatchResponse>(API_PATHS.agent.match, { post_id: postId })
}

/** AI 成队规划 */
export function generateTeamPlan(teamId: string) {
  return post<{
    division_of_labor: DivisionItem[]
    meeting_agenda: AgendaItem[]
    task_list: TaskItem[]
    risk_reminders: string[]
  }>(API_PATHS.agent.teamPlan, { team_id: teamId })
}
