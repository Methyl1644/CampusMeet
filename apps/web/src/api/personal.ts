import { get, patch } from './client'
import { API_PATHS } from '@shared/constants'
import type {
  ExploreActivityCard,
  ExploreGroupCard,
  MyActivityView,
  MyGroupView,
  PaginatedResponse,
  PersonalSettings,
  PersonalSettingsUpdate,
  PublicProfile,
} from '@shared/types'

const boundedPageSize = (value: number) => Math.min(40, Math.max(1, Math.trunc(value)))

export function getMyActivities(view: MyActivityView, page = 1, pageSize = 20) {
  return get<PaginatedResponse<ExploreActivityCard>>(API_PATHS.personal.activities, {
    view,
    page: Math.max(1, Math.trunc(page)),
    page_size: boundedPageSize(pageSize),
  })
}

export function getMyGroups(view: MyGroupView, page = 1, pageSize = 20) {
  return get<PaginatedResponse<ExploreGroupCard>>(API_PATHS.personal.groups, {
    view,
    page: Math.max(1, Math.trunc(page)),
    page_size: boundedPageSize(pageSize),
  })
}

export function getPublicProfile(userId: string) {
  return get<PublicProfile>(API_PATHS.personal.publicProfile.replace(':id', userId))
}

export function getPersonalSettings() {
  return get<PersonalSettings>(API_PATHS.personal.settings)
}

export function updatePersonalProfile(update: Omit<PersonalSettingsUpdate, 'notification_preferences'>) {
  return patch<PersonalSettings>(API_PATHS.personal.profile, update)
}

export function updatePersonalSettings(update: PersonalSettingsUpdate) {
  return patch<PersonalSettings>(API_PATHS.personal.settings, update)
}
