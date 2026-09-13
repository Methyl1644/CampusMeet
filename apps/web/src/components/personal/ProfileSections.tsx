import type { ReactNode } from 'react'
import { CalendarDays, Clock3, Sparkles, UsersRound } from 'lucide-react'
import ActivityCard from '@/components/explore/ActivityCard'
import GroupCard from '@/components/explore/GroupCard'
import type { PublicProfile } from '@shared/types'

function Section({ title, children }: { title: string; children: ReactNode }) {
  return <section className="border-b border-stone py-8"><h2 className="text-xl font-bold text-ink">{title}</h2><div className="mt-5">{children}</div></section>
}

function TagList({ icon, label, values }: { icon: ReactNode; label: string; values: string[] }) {
  return (
    <div>
      <p className="flex items-center gap-2 text-sm font-semibold text-ink">{icon}{label}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {values.map((value) => <span key={value} className="rounded-full bg-[#ECECEF] px-3 py-1.5 text-sm text-ink">{value}</span>)}
      </div>
    </div>
  )
}

export default function ProfileSections({ profile }: { profile: PublicProfile }) {
  return (
    <div>
      {(profile.interests?.length || profile.skills?.length) ? (
        <Section title="兴趣与能力">
          <div className="grid gap-6 md:grid-cols-2">
            {profile.interests && <TagList icon={<Sparkles aria-hidden="true" className="size-4" />} label="感兴趣" values={profile.interests} />}
            {profile.skills && <TagList icon={<UsersRound aria-hidden="true" className="size-4" />} label="擅长" values={profile.skills} />}
          </div>
        </Section>
      ) : null}
      {profile.availability && <Section title="可参与时间"><p className="flex items-center gap-2 text-sm text-ink-muted"><Clock3 aria-hidden="true" className="size-4" />已公开可参与时间，可在设置中调整。</p></Section>}
      <Section title="最近的活动">
        {profile.activities?.length ? <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">{profile.activities.map((item) => <ActivityCard key={item.id} activity={item} favoritePending={false} onFavorite={() => undefined} favoriteEnabled={false} />)}</div> : <p className="text-sm text-ink-muted">暂时没有公开活动。</p>}
      </Section>
      <Section title="最近的小组">
        {profile.groups?.length ? <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">{profile.groups.map((item) => <GroupCard key={item.id} group={item} favoritePending={false} onFavorite={() => undefined} favoriteEnabled={false} />)}</div> : <p className="text-sm text-ink-muted">暂时没有公开小组。</p>}
      </Section>
      <p className="sr-only"><CalendarDays />个人主页内容结束</p>
    </div>
  )
}
