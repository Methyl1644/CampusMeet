function SkeletonLine({ className }: { className: string }) {
  return <span className={`block rounded bg-[#E8E9ED] ${className}`} />
}

export default function HomeSkeleton() {
  return (
    <div
      role="status"
      aria-label="正在加载首页"
      className="grid min-w-0 animate-pulse grid-cols-1 gap-8 lg:grid-cols-[minmax(0,280px)_minmax(0,1fr)] lg:gap-10"
    >
      <span className="sr-only">正在加载首页</span>
      <aside data-testid="home-skeleton-sidebar" className="min-h-[32rem] min-w-0 space-y-5">
        <div className="flex items-center gap-3 px-1 py-2">
          <span className="size-14 shrink-0 rounded-full bg-[#E8E9ED]" />
          <div className="min-w-0 flex-1 space-y-2">
            <SkeletonLine className="h-4 w-28" />
            <SkeletonLine className="h-3 w-40 max-w-full" />
          </div>
        </div>
        <div className="min-h-[13rem] rounded-card border border-stone bg-paper p-4">
          <SkeletonLine className="h-5 w-24" />
          <SkeletonLine className="mt-5 h-[72px] w-full" />
          <SkeletonLine className="mt-4 h-3 w-32" />
        </div>
        <div className="min-h-32 rounded-card border border-stone bg-paper p-4">
          <SkeletonLine className="h-5 w-24" />
          <SkeletonLine className="mt-5 h-12 w-full" />
        </div>
      </aside>

      <div className="min-w-0 overflow-hidden">
        <SkeletonLine className="h-8 w-36" />
        <SkeletonLine className="mt-2 h-4 w-52" />
        <div className="mt-5 flex gap-4 overflow-hidden">
          {[0, 1, 2].map((item) => (
            <div
              key={item}
              data-testid="home-skeleton-event"
              className="h-[392px] w-[272px] shrink-0 overflow-hidden rounded-card border border-stone bg-paper"
            >
              <span className="block aspect-[16/9] w-full bg-[#E3E5EA]" />
              <div className="h-[238px] space-y-3 p-4">
                <SkeletonLine className="h-5 w-full" />
                <SkeletonLine className="h-5 w-4/5" />
                <SkeletonLine className="h-3 w-2/3" />
                <SkeletonLine className="h-3 w-1/2" />
              </div>
            </div>
          ))}
        </div>
        <div data-testid="home-skeleton-timeline" className="mt-10 min-h-[16rem]">
          <SkeletonLine className="h-7 w-44" />
          <SkeletonLine className="mt-2 h-4 w-40" />
          <div className="mt-5 space-y-px border-y border-stone bg-stone">
            {[0, 1, 2].map((item) => (
              <span key={item} className="block h-[76px] bg-paper" />
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
