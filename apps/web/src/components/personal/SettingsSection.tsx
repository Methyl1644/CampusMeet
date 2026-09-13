import type { ReactNode } from 'react'

export default function SettingsSection({ title, description, children, danger = false }: { title: string; description: string; children: ReactNode; danger?: boolean }) {
  return (
    <section className={`border-b py-7 ${danger ? 'border-red-200' : 'border-stone'}`}>
      <div className="grid gap-5 lg:grid-cols-[15rem_minmax(0,1fr)] lg:gap-10">
        <div><h2 className={`text-lg font-bold ${danger ? 'text-red-800' : 'text-ink'}`}>{title}</h2><p className="mt-2 text-sm leading-6 text-ink-muted">{description}</p></div>
        <div className="min-w-0">{children}</div>
      </div>
    </section>
  )
}
