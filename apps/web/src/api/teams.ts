import { client, get, patch, post } from './client'
import { API_PATHS } from '@shared/constants'
import type { PaginatedResponse, Team, TaskItem } from '@shared/types'

interface MyTeamsParams {
  page?: number
  page_size?: number
}

export interface MyTeamSummary {
  id: string
  post_id: string
  activity_name: string
  my_role: string | null
  created_at: string | null
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
  return get<PaginatedResponse<MyTeamSummary>>(
    API_PATHS.teams.myTeams,
    params as Record<string, unknown> | undefined,
    signal,
  )
}

export function createTask(teamId: string, body: { title: string; assignee_id?: number | null; due_at?: string }) {
  return post<TaskItem>(API_PATHS.teams.createTask.replace(':id', teamId), body)
}

export function editTask(teamId: string, taskId: string, body: { title: string; assignee_id?: number | null; due_at?: string }) {
  return patch<TaskItem>(API_PATHS.teams.editTask.replace(':id', teamId).replace(':taskId', taskId), body)
}

export async function deleteTask(teamId: string, taskId: string) {
  return (await client.delete(API_PATHS.teams.deleteTask.replace(':id', teamId).replace(':taskId', taskId))).data.data
}

export function reorderTasks(teamId: string, taskIds: string[]) {
  return post(API_PATHS.teams.reorderTasks.replace(':id', teamId), { task_ids: taskIds })
}

export function updateMemberRole(teamId: string, userId: string, suggestedRole: string) {
  return patch(API_PATHS.teams.detail.replace(':id', teamId) + `/members/${userId}/role`, { suggested_role: suggestedRole })
}

export async function removeMember(teamId: string, userId: string) {
  return (await client.delete(API_PATHS.teams.detail.replace(':id', teamId) + `/members/${userId}`)).data.data
}

export function leaveTeam(teamId: string) {
  return post(API_PATHS.teams.detail.replace(':id', teamId) + '/leave')
}

export function transferTeamOwner(teamId: string, userId: string) {
  return post(API_PATHS.teams.transferOwner.replace(':id', teamId), { target_user_id: Number(userId) })
}

export function archiveTeam(teamId: string) {
  return post<Team>(API_PATHS.teams.archive.replace(':id', teamId))
}
