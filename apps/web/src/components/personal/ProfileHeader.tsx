import { Pencil } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { PublicProfile } from '@shared/types'

export default function ProfileHeader({ profile }: { profile: PublicProfile }) {
  const initial = profile.nickname.trim().slice(0, 1) || '我'
  return (
    <header className="grid gap-6 border-b border-stone pb-8 sm:grid-cols-[7rem_minmax(0,1fr)_auto] sm:items-center">
      {profile.avatar ? (
        <img src={profile.avatar} alt={`${profile.nickname}的头像`} className="size-28 rounded-full object-cover" />
      ) : (
        <span className="flex size-28 items-center justify-center rounded-full bg-primary-100 text-4xl font-bold text-primary-700">{initial}</span>
      )}
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <h1 className="break-words text-3xl font-bold text-ink">{profile.nickname}</h1>
        </div>
        {(profile.major || profile.grade) && <p className="mt-2 text-sm text-ink-muted">{[profile.major, profile.grade].filter(Boolean).join(' · ')}</p>}
        {profile.bio && <p className="mt-4 max-w-2xl whitespace-pre-wrap text-sm leading-7 text-ink-muted">{profile.bio}</p>}
      </div>
      {profile.is_owner && <Link to="/settings" className="btn-secondary"><Pencil aria-hidden="true" className="size-4" />编辑资料</Link>}
    </header>
  )
}
