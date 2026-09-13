import { get, post } from './client'
import { API_PATHS } from '@shared/constants'
import type { Notification, PaginatedResponse } from '@shared/types'

export interface NotificationMutationResult {
  updated: number;
  unread_count: number;
  notification?: Notification;
}

export function getNotifications(page = 1, pageSize = 20) {
  return get<PaginatedResponse<Notification>>(API_PATHS.notifications.list, {
    page: Math.max(1, Math.trunc(page)),
    page_size: Math.min(40, Math.max(1, Math.trunc(pageSize))),
  })
}

export function markNotificationRead(id: string) {
  return post<Notification & { unread_count: number }>(API_PATHS.notifications.read.replace(':id', id))
}

export function markAllNotificationsRead() {
  return post<NotificationMutationResult>(API_PATHS.notifications.readAll)
}
