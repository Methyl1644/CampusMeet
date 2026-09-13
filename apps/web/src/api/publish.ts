import { get, post } from './client'
import type { UploadTicket } from '@shared/types'
import type { PublishContext } from '@/features/publish/publishState'

export function getPublishContext(kind: string, topicId?: string) {
  return get<PublishContext>('/api/publish/context', { kind, topic_id: topicId || '' })
}

export async function uploadPostCover(file: File): Promise<string> {
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > 10 * 1024 * 1024) {
    throw new Error('请选择 10MB 以内的 JPG、PNG 或 WebP 图片')
  }
  const ticket = await post<UploadTicket>('/api/uploads', { purpose: 'post_cover', filename: file.name, mime_type: file.type, size: file.size })
  const response = await fetch(ticket.upload.url, { method: 'PUT', headers: ticket.upload.headers, body: file, signal: AbortSignal.timeout(60000) })
  if (!response.ok) throw new Error('封面上传失败')
  await post(`/api/uploads/${ticket.upload_id}/complete`)
  return ticket.upload_id
}
