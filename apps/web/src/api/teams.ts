import { get, patch } from './client'
import { API_PATHS } from '@shared/constants'
import type { PaginatedResponse, Team, TaskItem } from '@shared/types'

interface MyTeamsParams {
  page?: number
  page_size?: number
}

/** 获取团队详情 */
export function getTeamDetail(id: string, signal?: AbortSignal) {
  return get<Team>(API_PATHS.teams.detail.replace(':id', id), undefined, signal)
}

/** 更新任务状态 */
export function updateTask(teamId: string, taskId: string, done: boolean) {
  return patch<TaskItem>(API_PATHS.teams.updateTask.replace(':id', teamId).replace(':taskId', taskId), { done })
}

/** 获取我的团队 */
export function getMyTeams(params?: MyTeamsParams, signal?: AbortSignal) {
  return get<PaginatedResponse<Team>>(
    API_PATHS.teams.myTeams,
    params as Record<string, unknown> | undefined,
    signal,
  )
}
