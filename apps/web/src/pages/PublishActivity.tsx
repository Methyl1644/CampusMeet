import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { CalendarPlus, Check, Image, MapPin } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { createTopic, getTags, type TopicCreateInput } from '@/api/content'
import { getApiErrorMessage } from '@/api/auth-feedback'
import { useAuthStore } from '@/store/authStore'
import type { StandardTag } from '@shared/types'
import { NJU_CAMPUSES } from '@/features/location/campuses'
import { attachPublicUpload, uploadTopicCover } from '@/api/publish'

const emptyForm = {
  title: '', short_title: '', organizer: '', edition: '', summary: '', content: '',
  source_url: '', cover_url: '', registration_deadline: '', activity_start_at: '',
  activity_end_at: '', location_name: '', campus_scope: '', capacity: '',
  participation_mode: 'official_signup' as TopicCreateInput['participation_mode'],
}

function isoOrNull(value: string) {
  return value ? new Date(value).toISOString() : null
}

export default function PublishActivity() {
  const user = useAuthStore((state) => state.user)
  const navigate = useNavigate()
  const identity = user?.identity
  const organizations = useMemo(() => identity?.organization_roles.filter(({ role }) => role === 'owner' || role === 'publisher') || [], [identity])
  const canPublishOfficial = Boolean(identity?.is_staff || identity?.platform_role)
  const canPublish = canPublishOfficial || organizations.length > 0
  const [channel, setChannel] = useState<'official' | 'organization'>(canPublishOfficial ? 'official' : 'organization')
  const [organizationId, setOrganizationId] = useState(organizations[0]?.organization_id || '')
  const [form, setForm] = useState(emptyForm)
  const [tags, setTags] = useState<StandardTag[]>([])
  const [selectedTags, setSelectedTags] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [coverUploadId, setCoverUploadId] = useState('')
  const [coverUploading, setCoverUploading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => { void getTags().then(setTags).catch(() => setError('活动标签暂时无法加载，请刷新后重试')) }, [])

  const update = <K extends keyof typeof emptyForm>(key: K, value: (typeof emptyForm)[K]) => setForm((current) => ({ ...current, [key]: value }))

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!selectedTags.length) { setError('请至少选择一个活动标签'); return }
    if (channel === 'organization' && !organizationId) { setError('请选择发布活动的认证组织'); return }
    setBusy(true); setError('')
    try {
      const topic = await createTopic({
        ...form,
        channel,
        organizer_key: form.organizer,
        canonical_event_key: form.short_title || form.title,
        registration_deadline: isoOrNull(form.registration_deadline),
        activity_start_at: isoOrNull(form.activity_start_at),
        activity_end_at: isoOrNull(form.activity_end_at),
        location_name: form.location_name.trim() || '暂无',
        capacity: form.capacity ? Number(form.capacity) : null,
        organization_id: channel === 'organization' ? Number(organizationId) : null,
        tag_ids: selectedTags,
      })
      if (coverUploadId) await attachPublicUpload(coverUploadId, topic.id)
      navigate(`/topics/${topic.id}`)
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, '正式活动发布失败，填写内容已保留'))
    } finally { setBusy(false) }
  }

  const uploadCover = async (file: File) => {
    setCoverUploading(true); setError('')
    try {
      setCoverUploadId(await uploadTopicCover(file))
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, '活动封面上传失败，请重试'))
    } finally { setCoverUploading(false) }
  }

  if (!canPublish) return <div className="mx-auto max-w-2xl py-16 text-center"><CalendarPlus className="mx-auto size-10 text-ink-muted" /><h1 className="mt-4 text-2xl font-bold">暂无正式活动发布权限</h1><p className="mt-2 text-sm text-ink-muted">接受平台或认证组织的发布者邀请后，此入口会自动开放。</p><Link className="btn-secondary mt-5" to="/authorizations">查看我的授权</Link></div>

  return (
    <div className="mx-auto max-w-5xl animate-slide-up pb-12">
      <header className="flex flex-wrap items-end justify-between gap-4 border-b border-stone pb-6">
        <div><p className="section-label">官方内容</p><h1 className="mt-3 font-serif text-3xl font-semibold text-ink">发布正式活动</h1><p className="mt-2 text-sm text-ink-muted">发布后你将自动成为活动负责人，可以在管理中心邀请组织者和协作成员。</p></div>
        <Link className="btn-secondary" to="/publish">返回发布组队帖</Link>
      </header>
      <form onSubmit={submit} className="mt-6 space-y-7">
        {canPublishOfficial && organizations.length > 0 && <fieldset><legend className="text-sm font-bold">发布身份</legend><div className="mt-2 flex gap-2"><button type="button" className={channel === 'official' ? 'btn-primary' : 'btn-secondary'} onClick={() => setChannel('official')}>平台正式活动</button><button type="button" className={channel === 'organization' ? 'btn-primary' : 'btn-secondary'} onClick={() => setChannel('organization')}>认证组织活动</button></div></fieldset>}
        {channel === 'organization' && <label className="block text-sm font-bold">发布组织<select required className="input-base mt-2" value={organizationId} onChange={(e) => setOrganizationId(e.target.value)}>{organizations.map((organization) => <option key={organization.organization_id} value={organization.organization_id}>{organization.organization_name}</option>)}</select></label>}
        <section className="grid gap-4 sm:grid-cols-2">
          <label className="text-sm font-bold sm:col-span-2">活动标题<input required maxLength={120} className="input-base mt-2" value={form.title} onChange={(e) => update('title', e.target.value)} /></label>
          <label className="text-sm font-bold">活动简称<input required maxLength={60} className="input-base mt-2" value={form.short_title} onChange={(e) => update('short_title', e.target.value)} /></label>
          <label className="text-sm font-bold">届次或学期<input required maxLength={40} className="input-base mt-2" placeholder="例如 2026 秋" value={form.edition} onChange={(e) => update('edition', e.target.value)} /></label>
          <label className="text-sm font-bold sm:col-span-2">主办方<input required maxLength={120} className="input-base mt-2" value={form.organizer} onChange={(e) => update('organizer', e.target.value)} /></label>
          <label className="text-sm font-bold sm:col-span-2">活动简介<textarea required maxLength={600} rows={3} className="input-base mt-2 resize-y" value={form.summary} onChange={(e) => update('summary', e.target.value)} /></label>
          <label className="text-sm font-bold sm:col-span-2">活动详情<textarea required maxLength={8000} rows={8} className="input-base mt-2 resize-y" value={form.content} onChange={(e) => update('content', e.target.value)} /></label>
        </section>
        <section className="grid gap-4 border-t border-stone pt-6 sm:grid-cols-3">
          <p className="text-sm text-ink-muted sm:col-span-3">时间尚未确定时可以留空，地点尚未确定时可填写“暂无”；活动负责人发布后可继续补充。</p>
          <label className="text-sm font-bold"><CalendarPlus className="mr-1 inline size-4" />报名截止<input type="datetime-local" className="input-base mt-2" value={form.registration_deadline} onChange={(e) => update('registration_deadline', e.target.value)} /></label>
          <label className="text-sm font-bold">活动开始<input type="datetime-local" className="input-base mt-2" value={form.activity_start_at} onChange={(e) => update('activity_start_at', e.target.value)} /></label>
          <label className="text-sm font-bold">活动结束<input type="datetime-local" className="input-base mt-2" value={form.activity_end_at} onChange={(e) => update('activity_end_at', e.target.value)} /></label>
          <label className="text-sm font-bold"><MapPin className="mr-1 inline size-4" />地点<input maxLength={200} className="input-base mt-2" value={form.location_name} onChange={(e) => update('location_name', e.target.value)} /></label>
          <label className="text-sm font-bold">校区<select className="input-base mt-2" value={form.campus_scope} onChange={(e) => update('campus_scope', e.target.value)}><option value="">请选择校区</option>{NJU_CAMPUSES.map((campus) => <option key={campus} value={campus}>{campus}</option>)}</select></label>
          <label className="text-sm font-bold">人数上限<input type="number" min={1} max={100000} className="input-base mt-2" value={form.capacity} onChange={(e) => update('capacity', e.target.value)} /></label>
          <label className="text-sm font-bold">参与方式<select className="input-base mt-2" value={form.participation_mode} onChange={(e) => update('participation_mode', e.target.value as TopicCreateInput['participation_mode'])}><option value="official_signup">官方报名</option><option value="open_team">允许发布组队帖</option><option value="information_only">仅展示信息</option></select></label>
          <div className="text-sm font-bold"><Image className="mr-1 inline size-4" />活动封面 <span className="font-normal text-ink-muted">（选填，留空自动生成）</span><label className={`btn-secondary mt-2 flex min-h-11 cursor-pointer ${coverUploading ? 'pointer-events-none opacity-50' : ''}`}>{coverUploading ? '上传中...' : coverUploadId ? '重新上传封面' : '上传活动封面'}<input type="file" className="sr-only" accept="image/jpeg,image/png,image/webp" aria-label="上传活动封面" disabled={coverUploading} onChange={(event) => { const file = event.target.files?.[0]; if (file) void uploadCover(file); event.target.value = '' }} /></label>{coverUploadId && <span className="mt-2 block text-xs font-normal text-emerald-700">封面已上传</span>}<label className="mt-2 block font-normal">或填写图片网址<input type="url" maxLength={500} className="input-base mt-2" value={form.cover_url} onChange={(e) => update('cover_url', e.target.value)} /></label></div>
          <label className="text-sm font-bold">官方来源网址<input type="url" maxLength={500} className="input-base mt-2" value={form.source_url} onChange={(e) => update('source_url', e.target.value)} /></label>
        </section>
        <fieldset className="border-t border-stone pt-6"><legend className="text-sm font-bold">活动标签</legend><div className="mt-3 flex flex-wrap gap-2">{tags.map((tag) => { const selected = selectedTags.includes(tag.tag_id); return <button key={tag.tag_id} type="button" aria-pressed={selected} className={selected ? 'btn-primary' : 'btn-secondary'} onClick={() => setSelectedTags((current) => selected ? current.filter((id) => id !== tag.tag_id) : current.length < 8 ? [...current, tag.tag_id] : current)}>{selected && <Check className="size-4" />}{tag.canonical_name}</button> })}</div></fieldset>
        {error && <p role="alert" className="rounded-card border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
        <div className="flex justify-end border-t border-stone pt-6"><button type="submit" className="btn-primary" disabled={busy || coverUploading}><CalendarPlus className="size-4" />{busy ? '发布中...' : '发布正式活动'}</button></div>
      </form>
    </div>
  )
}
