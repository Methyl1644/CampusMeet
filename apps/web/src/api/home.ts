import { API_PATHS } from '@shared/constants'
import type { HomeFeed, HomeWarningSection } from '@shared/types'
import { get } from './client'

export function getHomeFeed(): Promise<HomeFeed> {
  return get<HomeFeed>(API_PATHS.home.feed)
}

export function homeSectionState(
  feed: HomeFeed,
  section: HomeWarningSection,
): 'ready' | 'degraded' {
  return feed.warnings.includes(section) ? 'degraded' : 'ready'
}
