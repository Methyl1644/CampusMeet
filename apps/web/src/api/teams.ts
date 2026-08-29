import { get, patch } from './client'
import { API_PATHS } from '@shared/constants'
import type { Team, TaskItem } from '@shared/types'

/** 获取团队详情 */
export function getTeamDetail(id: string) {
  return get<Team>(API_PATHS.teams.detail.replace(':id', id))
}

/** 更新任务状态 */
export function updateTask(teamId: string, taskId: string, done: boolean) {
  return patch<TaskItem>(API_PATHS.teams.updateTask.replace(':id', teamId).replace(':taskId', taskId), { done })
}

/** 获取我的团队 */
export function getMyTeams() {
  return get<Team[]>(API_PATHS.teams.myTeams)
}
