import { useCallback, useEffect, useState } from 'react'
import { RefreshCw } from 'lucide-react'
import { useParams } from 'react-router-dom'
import { getPublicProfile } from '@/api/personal'
import ProfileHeader from '@/components/personal/ProfileHeader'
import ProfileSections from '@/components/personal/ProfileSections'
import { useAuthStore } from '@/store/authStore'
import type { PublicProfile as PublicProfileData } from '@shared/types'

export default function PublicProfile() {
  const { id = 'me' } = useParams()
  const user = useAuthStore((state) => state.user)
  const resolvedId = id === 'me' ? user?.id : id
  const [profile, setProfile] = useState<PublicProfileData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  const load = useCallback(async () => {
    if (!resolvedId) return
    setLoading(true)
    setError(false)
    try { setProfile(await getPublicProfile(resolvedId)) } catch { setError(true) } finally { setLoading(false) }
  }, [resolvedId])

  useEffect(() => { void load() }, [load])
  if (loading) return <div role="status" className="grid min-h-80 place-items-center text-sm text-ink-muted">正在加载个人主页...</div>
  if (error || !profile) return <div role="alert" className="grid min-h-80 place-items-center text-center"><div><p className="font-semibold">个人主页暂时无法加载</p><button type="button" onClick={() => void load()} className="btn-secondary mt-4"><RefreshCw aria-hidden="true" className="size-4" />重试</button></div></div>
  return <div className="mx-auto max-w-6xl animate-slide-up"><ProfileHeader profile={profile} /><ProfileSections profile={profile} /></div>
}
