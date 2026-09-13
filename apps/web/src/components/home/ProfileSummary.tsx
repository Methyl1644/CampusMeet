import { ArrowUpRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { HomeProfile } from '@shared/types'

export default function ProfileSummary({ profile }: { profile: HomeProfile }) {
  const details = [profile.major, profile.grade].filter(Boolean).join(' · ')
  const fallbackInitial = profile.nickname.trim().charAt(0) || '我'

  return (
    <section aria-labelledby="home-profile-name" className="flex min-w-0 items-center gap-3 px-1 py-2">
      {profile.avatar ? (
        <img
          src={profile.avatar}
          alt={`${profile.nickname}的头像`}
          className="size-14 shrink-0 rounded-full object-cover"
        />
      ) : (
        <span
          role="img"
          aria-label={`${profile.nickname}的头像`}
          className="flex size-14 shrink-0 items-center justify-center rounded-full bg-primary-100 text-lg font-semibold text-primary-700"
        >
          {fallbackInitial}
        </span>
      )}

      <div className="min-w-0 flex-1">
        <h2 id="home-profile-name" className="truncate text-base font-semibold text-ink">
          {profile.nickname}
        </h2>
        <p className="mt-0.5 truncate text-sm text-ink-muted">
          {details || '专业与年级待完善'}
        </p>
        <Link
          to="/users/me"
          className="mt-1.5 inline-flex items-center gap-1 text-sm font-semibold text-primary-700 transition-colors duration-fast hover:text-primary-800"
        >
          查看个人主页
          <ArrowUpRight aria-hidden="true" className="size-3.5" />
        </Link>
      </div>
    </section>
  )
}
