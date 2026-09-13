import type { ReactNode } from 'react'

export default function StickyActions({
  label,
  children,
}: {
  label: string
  children: ReactNode
}) {
  return (
    <aside
      role="region"
      aria-label={label}
      data-mobile-safe-area="true"
      className="fixed inset-x-0 bottom-[calc(4rem+env(safe-area-inset-bottom))] z-30 border-y border-stone bg-paper/95 px-4 py-3 shadow-[0_-4px_16px_rgb(33_29_36_/_0.08)] backdrop-blur md:sticky md:inset-x-auto md:bottom-4 md:mt-8 md:rounded-card md:border md:px-5"
    >
      <div className="mx-auto flex min-h-11 max-w-5xl items-center justify-end gap-2">
        {children}
      </div>
    </aside>
  )
}
