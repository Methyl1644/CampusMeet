import type { ExploreActivityCard, ExploreGroupCard } from '@shared/types'
import type { ExploreView } from '@/features/explore/exploreState'
import ActivityCard from './ActivityCard'
import GroupCard from './GroupCard'

interface ExploreGridProps {
  view: ExploreView
  activities: ExploreActivityCard[]
  groups: ExploreGroupCard[]
  favoritePending: ReadonlySet<string>
  onActivityFavorite: (id: string, favorite: boolean) => void
  onGroupFavorite: (id: string, favorite: boolean) => void
}

export default function ExploreGrid({ view, activities, groups, favoritePending, onActivityFavorite, onGroupFavorite }: ExploreGridProps) {
  return (
    <div className="grid min-w-0 gap-5 sm:grid-cols-2 lg:grid-cols-3">
      {view === 'activity'
        ? activities.map((activity) => <ActivityCard key={activity.id} activity={activity} favoritePending={favoritePending.has(`activity:${activity.id}`)} onFavorite={onActivityFavorite} />)
        : groups.map((group) => <GroupCard key={group.id} group={group} favoritePending={favoritePending.has(`group:${group.id}`)} onFavorite={onGroupFavorite} />)}
    </div>
  )
}
