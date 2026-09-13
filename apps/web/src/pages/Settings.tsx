import { useCallback, useEffect, useState } from 'react'
import { Save, ShieldAlert } from 'lucide-react'
import { changePassword, deactivateAccount } from '@/api/auth'
import { getPersonalSettings, updatePersonalProfile, updatePersonalSettings } from '@/api/personal'
import SettingsSection from '@/components/personal/SettingsSection'
import { useToast } from '@/components/Toast'
import { useAuthStore } from '@/store/authStore'
import type { NotificationPreferences, PersonalSettings, ProfileVisibility } from '@shared/types'

const visibilityLabels = { major: '专业', grade: '年级', interests: '兴趣', skills: '技能', availability: '可参与时间', contact: '联系方式', activities: '最近活动', groups: '最近小组' } as const
const preferenceLabels: Record<keyof NotificationPreferences, string> = { applications: '申请动态', teams: '团队动态', moderation: '内容审核', deadlines: '截止提醒', messages: '新消息' }

export default function Settings() {
  const [draft, setDraft] = useState<PersonalSettings | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [deactivatePassword, setDeactivatePassword] = useState('')
  const { showToast } = useToast()
  const { logout, updateUser } = useAuthStore()

  const load = useCallback(async () => {
    setLoading(true)
    try { setDraft(await getPersonalSettings()) } catch { showToast('设置加载失败，请稍后重试', 'error') } finally { setLoading(false) }
  }, [showToast])
  useEffect(() => { void load() }, [load])

  const save = async () => {
    if (!draft || saving) return
    setSaving(true)
    try {
      await updatePersonalProfile({
        nickname: draft.nickname, avatar: draft.avatar, bio: draft.bio ?? '',
        major: draft.major?.trim() || undefined, grade: draft.grade?.trim() || undefined,
        interests: draft.interests, looking_for: draft.looking_for,
        skills: draft.skills, availability: draft.availability,
      })
      const saved = await updatePersonalSettings({ profile_visibility: draft.profile_visibility, notification_preferences: draft.notification_preferences })
      setDraft(saved)
      updateUser({ nickname: saved.nickname, avatar: saved.avatar ?? undefined, major: saved.major ?? undefined, grade: saved.grade ?? undefined, skills: saved.skills, interests: saved.interests, availability: saved.availability, profile_visibility: saved.profile_visibility, bio: saved.bio })
      showToast('设置已保存', 'success')
    } catch { showToast('保存失败，填写内容已保留', 'error') } finally { setSaving(false) }
  }

  if (loading && !draft) return <div role="status" className="grid min-h-80 place-items-center text-sm text-ink-muted">正在加载设置...</div>
  if (!draft) return <div role="alert" className="grid min-h-80 place-items-center"><button type="button" className="btn-secondary" onClick={() => void load()}>重新加载设置</button></div>

  return (
    <div className="mx-auto max-w-5xl animate-slide-up">
      <header className="border-b border-stone pb-6"><p className="section-label">账号管理</p><h1 className="mt-3 text-3xl font-bold text-ink">设置</h1></header>
      <SettingsSection title="个人资料" description="这些内容会根据下方隐私开关显示在个人主页。">
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="text-sm font-semibold">昵称<input className="input-base mt-2" value={draft.nickname} onChange={(event) => setDraft({ ...draft, nickname: event.target.value })} /></label>
          <label className="text-sm font-semibold">专业<input className="input-base mt-2" value={draft.major ?? ''} onChange={(event) => setDraft({ ...draft, major: event.target.value })} /></label>
          <label className="text-sm font-semibold">年级<input className="input-base mt-2" value={draft.grade ?? ''} onChange={(event) => setDraft({ ...draft, grade: event.target.value })} /></label>
          <label className="text-sm font-semibold sm:col-span-2">个人简介<textarea className="input-base mt-2 min-h-28 resize-y" value={draft.bio ?? ''} onChange={(event) => setDraft({ ...draft, bio: event.target.value })} /></label>
        </div>
      </SettingsSection>
      <SettingsSection title="主页隐私" description="关闭后，对应字段不会出现在其他同学看到的主页响应中。">
        <div className="divide-y divide-stone">{Object.entries(visibilityLabels).map(([key, label]) => <Toggle key={key} label={label} checked={Boolean(draft.profile_visibility[key as keyof ProfileVisibility])} onChange={(checked) => setDraft({ ...draft, profile_visibility: { ...draft.profile_visibility, [key]: checked } })} />)}</div>
      </SettingsSection>
      <SettingsSection title="通知偏好" description="选择希望在站内通知中心接收的提醒。">
        <div className="divide-y divide-stone">{Object.entries(preferenceLabels).map(([key, label]) => <Toggle key={key} label={label} checked={draft.notification_preferences[key as keyof NotificationPreferences]} onChange={(checked) => setDraft({ ...draft, notification_preferences: { ...draft.notification_preferences, [key]: checked } })} />)}</div>
      </SettingsSection>
      <div className="flex justify-end py-6"><button type="button" className="btn-primary" disabled={saving} onClick={save}><Save aria-hidden="true" className="size-4" />{saving ? '保存中...' : '保存设置'}</button></div>
      <SettingsSection title="修改密码" description="修改后需要使用新密码重新登录。">
        <div className="grid gap-3 sm:grid-cols-2"><input aria-label="当前密码" type="password" className="input-base" placeholder="当前密码" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} /><input aria-label="新密码" type="password" className="input-base" placeholder="至少 8 位，同时包含字母和数字" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} /><button type="button" className="btn-secondary sm:col-span-2 sm:justify-self-start" onClick={async () => { try { await changePassword(currentPassword, newPassword); logout(); window.location.href = '/login' } catch { showToast('密码修改失败，请检查当前密码和新密码', 'error') } }}>修改密码</button></div>
      </SettingsSection>
      <SettingsSection title="停用账号" description="停用会立即退出当前账号，重新启用需要联系平台运营人员。" danger>
        <div className="flex flex-col gap-3 sm:flex-row"><input aria-label="停用账号当前密码" type="password" className="input-base" placeholder="输入当前密码确认" value={deactivatePassword} onChange={(e) => setDeactivatePassword(e.target.value)} /><button type="button" className="btn-secondary shrink-0 text-red-800" onClick={async () => { if (!window.confirm('确认停用账号？')) return; try { await deactivateAccount(deactivatePassword); logout(); window.location.href = '/login' } catch { showToast('账号停用失败', 'error') } }}><ShieldAlert aria-hidden="true" className="size-4" />停用账号</button></div>
      </SettingsSection>
    </div>
  )
}

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (checked: boolean) => void }) {
  return <label className="flex min-h-14 cursor-pointer items-center justify-between gap-4 py-3 text-sm font-medium text-ink"><span>{label}</span><input type="checkbox" className="size-5 accent-primary-700" checked={checked} onChange={(event) => onChange(event.target.checked)} /></label>
}
