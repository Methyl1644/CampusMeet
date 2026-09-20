import { client, get, post } from './client'
import { API_PATHS } from '@shared/constants'
import type { Application, CreateApplicationRequest, PaginatedResponse } from '@shared/types'

const backendHealthAttempts = 4
const backendHealthRetryDelayMs = 1500

async function waitForBackendReady() {
  let lastError: unknown
  for (let attempt = 0; attempt < backendHealthAttempts; attempt += 1) {
    try {
      await client.get('/health', { timeout: 10000 })
      return
    } catch (error) {
      lastError = error
      if (attempt < backendHealthAttempts - 1) {
        await new Promise((resolve) => window.setTimeout(resolve, backendHealthRetryDelayMs))
      }
    }
  }
  throw lastError
}

/** 创建申请 */
export async function createApplication(data: CreateApplicationRequest) {
  try {
    return await post<Application>(API_PATHS.applications.create, data)
  } catch (error) {
    const requestError = error as { code?: string; response?: unknown }
    const retryable = requestError.code === 'ERR_NETWORK'
      || requestError.code === 'ECONNABORTED'
      || !requestError.response
    if (!retryable) throw error
    await waitForBackendReady()
    return post<Application>(API_PATHS.applications.create, data)
  }
}

/** 获取我的申请 */
export function getMyApplications() {
  return get<PaginatedResponse<Application>>(API_PATHS.applications.myApplications)
}

/** 获取某帖子的申请列表（发布者视角） */
export function getPostApplications(postId: string) {
  return get<PaginatedResponse<Application>>(API_PATHS.applications.list, { post_id: postId })
}

/** 接受申请 */
export function acceptApplication(id: string) {
  return post<{ accepted: boolean; conversation_id: string }>(API_PATHS.applications.accept.replace(':id', id))
}

/** 拒绝申请 */
export function rejectApplication(id: string) {
  return post<{ rejected: boolean }>(API_PATHS.applications.reject.replace(':id', id))
}

export function withdrawApplication(id: string) {
  return post<{ withdrawn: boolean }>(API_PATHS.applications.withdraw.replace(':id', id))
}
