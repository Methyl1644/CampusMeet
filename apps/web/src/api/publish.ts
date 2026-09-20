import { get, post } from './client'
import type { UploadTicket } from '@shared/types'
import type { PublishContext } from '@/features/publish/publishState'

/** Fields the server accepts back on completion; anything else is rejected. */
const CLOUDINARY_RESULT_FIELDS = [
  'public_id',
  'version',
  'signature',
  'asset_id',
  'resource_type',
  'type',
  'format',
  'bytes',
] as const

export function getPublishContext(kind: string, topicId?: string) {
  return get<PublishContext>('/api/publish/context', { kind, topic_id: topicId || '' })
}

function pickCloudinaryResult(payload: unknown): Record<string, unknown> {
  const source = (payload ?? {}) as Record<string, unknown>
  const picked: Record<string, unknown> = {}
  for (const field of CLOUDINARY_RESULT_FIELDS) {
    if (source[field] !== undefined && source[field] !== null) picked[field] = source[field]
  }
  return picked
}

async function uploadPublicImage(file: File, purpose: 'post_cover' | 'topic_cover'): Promise<string> {
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > 10 * 1024 * 1024) {
    throw new Error('请选择 10MB 以内的 JPG、PNG 或 WebP 图片')
  }
  const ticket = await post<UploadTicket>('/api/uploads', { purpose, filename: file.name, mime_type: file.type, size: file.size })

  if (ticket.upload.provider === 'cloudinary') {
    const { url, fields, file_field: fileField } = ticket.upload
    const form = new FormData()
    for (const [name, value] of Object.entries(fields)) form.append(name, value)
    form.append(fileField || 'file', file)
    // Content-Type is left unset so the browser writes the multipart boundary.
    const response = await fetch(url, { method: 'POST', body: form, signal: AbortSignal.timeout(60000) })
    if (!response.ok) throw new Error(`封面上传失败（存储返回 ${response.status}）`)
    await post(`/api/uploads/${ticket.upload_id}/complete`, pickCloudinaryResult(await response.json()))
    return ticket.upload_id
  }

  const response = await fetch(ticket.upload.url, { method: 'PUT', headers: ticket.upload.headers, body: file, signal: AbortSignal.timeout(60000) })
  if (!response.ok) throw new Error(`封面上传失败（存储返回 ${response.status}）`)
  await post(`/api/uploads/${ticket.upload_id}/complete`)
  return ticket.upload_id
}

export function uploadPostCover(file: File): Promise<string> {
  return uploadPublicImage(file, 'post_cover')
}

export function uploadTopicCover(file: File): Promise<string> {
  return uploadPublicImage(file, 'topic_cover')
}

export function attachPublicUpload(uploadId: string, targetId: string) {
  return post<{ upload_id: string; purpose: string; status: string; target_id: string }>(`/api/uploads/${uploadId}/attach`, { target_id: Number(targetId) })
}
