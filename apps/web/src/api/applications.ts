import { get, post } from './client'
import { API_PATHS } from '@shared/constants'
import type { Application, CreateApplicationRequest } from '@shared/types'

/** 创建申请 */
export function createApplication(data: CreateApplicationRequest) {
  return post<Application>(API_PATHS.applications.create, data)
}

/** 获取我的申请 */
export function getMyApplications() {
  return get<Application[]>(API_PATHS.applications.myApplications)
}

/** 获取某帖子的申请列表（发布者视角） */
export function getPostApplications(postId: string) {
  return get<Application[]>(API_PATHS.applications.list, { post_id: postId })
}

/** 接受申请 */
export function acceptApplication(id: string) {
  return post<{ accepted: boolean }>(API_PATHS.applications.accept.replace(':id', id))
}

/** 拒绝申请 */
export function rejectApplication(id: string) {
  return post<{ rejected: boolean }>(API_PATHS.applications.reject.replace(':id', id))
}
