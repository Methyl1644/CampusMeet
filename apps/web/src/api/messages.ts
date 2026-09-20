import { get, post } from './client'
import { API_PATHS } from '@shared/constants'
import type { Conversation, Message, PaginatedResponse } from '@shared/types'

/** 获取会话列表 */
export async function getConversations() {
  return (await get<PaginatedResponse<Conversation>>(API_PATHS.messages.conversations)).list
}

/** 获取单个会话的最新状态，供当前聊天轻量轮询。 */
export function getConversation(conversationId: string) {
  return get<Conversation>(
    API_PATHS.messages.conversation.replace(':conversationId', conversationId),
  )
}

/** 获取某个会话的消息列表 */
export async function getMessages(
  conversationId: string,
  options: { latest?: boolean; before_id?: string; after_id?: string; page_size?: number } = {},
) {
  return get<PaginatedResponse<Message>>(
    API_PATHS.messages.messages.replace(':conversationId', conversationId),
    options,
  )
}

/** 发送消息 */
export function sendMessage(conversationId: string, content: string) {
  return post<Message>(API_PATHS.messages.send.replace(':conversationId', conversationId), { content })
}

/** 确认组队 */
export function confirmTeam(conversationId: string) {
  return post<{
    confirmed: boolean
    waiting_for_other?: boolean
    contact_unlocked?: boolean
    team_id?: string
  }>(API_PATHS.messages.confirmTeam.replace(':conversationId', conversationId))
}

/** 结束对话 */
export function closeConversation(conversationId: string) {
  return post<{ closed: boolean }>(API_PATHS.messages.close.replace(':conversationId', conversationId))
}
