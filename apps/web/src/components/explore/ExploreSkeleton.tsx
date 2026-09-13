export default function ExploreSkeleton({ view }: { view: 'activity' | 'group' }) {
  return (
    <div role="status" aria-label={`正在加载${view === 'activity' ? '活动' : '组队'}`} className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
      <span className="sr-only">正在加载，请稍候</span>
      {[0, 1, 2, 3, 4, 5].map((item) => (
        <div key={item} aria-hidden="true" className={`${view === 'activity' ? 'h-[432px]' : 'h-[444px]'} overflow-hidden rounded-card border border-stone bg-paper`}>
          <div className="aspect-[16/9] animate-pulse rounded-t-[12px] bg-[#E8EBEF]" />
          <div className="space-y-3 p-4">
            <div className="h-4 w-2/5 animate-pulse rounded bg-[#E8EBEF]" />
            <div className="h-5 w-full animate-pulse rounded bg-[#E8EBEF]" />
            <div className="h-5 w-4/5 animate-pulse rounded bg-[#E8EBEF]" />
            <div className="h-4 w-3/5 animate-pulse rounded bg-[#E8EBEF]" />
          </div>
        </div>
      ))}
    </div>
  )
}
