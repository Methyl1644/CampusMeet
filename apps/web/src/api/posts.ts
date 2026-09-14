import { client, get, patch, post } from './client'
import { API_PATHS } from '@shared/constants'
import type { Post, PaginatedResponse, PostPurpose } from '@shared/types'

/** 帖子列表查询参数 */
export interface PostListParams {
  category?: string
  tags?: string[]
  keyword?: string
  sort?: 'latest' | 'hot' | 'deadline'
  tab?: 'recommend' | 'recruiting' | 'official' | 'hot'
  page?: number
  page_size?: number
  kind?: 'topic_team' | 'casual_invitation'
  topic_id?: string
}

/** 获取帖子列表 */
export function getPosts(params: PostListParams) {
  const query = {
    ...params,
    tags: params.tags?.join(','),
  }
  return get<PaginatedResponse<Post>>(API_PATHS.posts.list, query as Record<string, unknown>)
}

/** 获取帖子详情 */
export function getPostDetail(id: string) {
  return get<Post>(API_PATHS.posts.detail.replace(':id', id))
}

/** 创建帖子 */
export function createPost(data: Partial<Post> & { purpose?: PostPurpose; client_request_id?: string; cover_upload_id?: string; publish_context_revision?: string }) {
  return post<Post>(API_PATHS.posts.create, data)
}

/** 获取我的帖子 */
export function getMyPosts() {
  return get<Post[]>(API_PATHS.posts.myPosts)
}

export function updatePost(id: string, data: Partial<Post>) {
  return patch<Post>(API_PATHS.posts.detail.replace(':id', id), data)
}

export function closePost(id: string) {
  return post<Post>(API_PATHS.posts.close.replace(':id', id))
}

export function reopenPost(id: string) {
  return post<Post>(API_PATHS.posts.reopen.replace(':id', id))
}

export function archivePost(id: string) {
  return post<Post>(API_PATHS.posts.archive.replace(':id', id))
}

export async function deletePost(id: string) {
  return (await client.delete(API_PATHS.posts.remove.replace(':id', id))).data.data as Post
}
