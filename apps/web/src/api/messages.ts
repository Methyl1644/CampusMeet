import { get, post } from './client'
import { API_PATHS } from '@shared/constants'
import type { Conversation, Message, PaginatedResponse } from '@shared/types'

/** 获取会话列表 */
export async function getConversations() {
  return (await get<PaginatedResponse<Conversation>>(API_PATHS.messages.conversations)).list
}

/** 获取某个会话的消息列表 */
export async function getMessages(conversationId: string) {
  return (await get<PaginatedResponse<Message>>(API_PATHS.messages.messages.replace(':conversationId', conversationId))).list
}

/** 发送消息 */
export function sendMessage(conversationId: string, content: string) {
  return post<Message>(API_PATHS.messages.send.replace(':conversationId', conversationId), { content })
}

/** 确认组队 */
export function confirmTeam(conversationId: string) {
  return post<{ confirmed: boolean }>(API_PATHS.messages.confirmTeam.replace(':conversationId', conversationId))
}

/** 结束对话 */
export function closeConversation(conversationId: string) {
  return post<{ closed: boolean }>(API_PATHS.messages.close.replace(':conversationId', conversationId))
}
