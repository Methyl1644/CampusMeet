import { useEffect, useMemo, useState } from 'react'
import { Building2, ClipboardCheck, ShieldCheck, UsersRound } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import PlatformRolesPanel from '@/features/management/PlatformRolesPanel'
import OrganizationReviewsPanel from '@/features/management/OrganizationReviewsPanel'
import OrganizationMembersPanel from '@/features/management/OrganizationMembersPanel'
import TopicCollaboratorsPanel from '@/features/management/TopicCollaboratorsPanel'
import {
  deriveManagementSections,
  type ManagementSectionId,
} from '@/features/management/managementAccess'
import { useAuthStore } from '@/store/authStore'

const sectionMeta: Record<ManagementSectionId, { label: string; icon: LucideIcon }> = {
  'platform-roles': { label: '平台角色', icon: ShieldCheck },
  'organization-reviews': { label: '组织审核', icon: ClipboardCheck },
  'organization-members': { label: '组织成员', icon: Building2 },
  'activity-collaborators': { label: '活动协作者', icon: UsersRound },
}

export default function Management() {
  const user = useAuthStore((state) => state.user)
  const sections = useMemo(() => deriveManagementSections(user?.identity), [user?.identity])
  const [activeSection, setActiveSection] = useState<ManagementSectionId | null>(sections[0] || null)

  useEffect(() => {
    if (!activeSection || !sections.includes(activeSection)) {
      setActiveSection(sections[0] || null)
    }
  }, [activeSection, sections])

  if (!user || sections.length === 0 || !activeSection) {
    return (
      <div className="mx-auto max-w-2xl py-12 text-center">
        <ShieldCheck aria-hidden="true" className="mx-auto size-10 text-ink-muted" />
        <h1 className="mt-5 text-2xl font-bold text-ink">暂无管理权限</h1>
        <p className="mt-2 text-sm leading-6 text-ink-muted">管理中心仅对平台运营、组织负责人和活动主管理员开放。</p>
      </div>
    )
  }

  const suggestedTopicId = user.identity?.topic_roles.find(({ role }) => role === 'manager')?.topic_id

  return (
    <div className="mx-auto max-w-6xl animate-slide-up">
      <header className="border-b border-stone pb-6">
        <p className="section-label">权限与责任范围</p>
        <h1 className="mt-3 text-3xl font-bold text-ink">管理中心</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-ink-muted">集中管理平台身份、认证组织和官方活动协作者。每项操作都会再次经过服务器权限校验。</p>
      </header>

      <div className="mt-6 grid min-w-0 gap-6 lg:grid-cols-[13rem_minmax(0,1fr)]">
        <nav aria-label="管理中心栏目" className="flex gap-2 overflow-x-auto border-b border-stone pb-3 lg:block lg:overflow-visible lg:border-b-0 lg:border-r lg:pb-0 lg:pr-5">
          {sections.map((section) => {
            const { label, icon: Icon } = sectionMeta[section]
            const selected = activeSection === section
            return (
              <button
                key={section}
                type="button"
                aria-pressed={selected}
                onClick={() => setActiveSection(section)}
                className={`flex min-h-11 shrink-0 items-center gap-2 rounded-card px-3 text-sm font-semibold transition duration-fast lg:mb-1 lg:w-full ${selected ? 'bg-primary-100 text-primary-800' : 'text-ink-muted hover:bg-paper hover:text-ink'}`}
              >
                <Icon aria-hidden="true" className="size-[18px]" />{label}
              </button>
            )
          })}
        </nav>

        <div className="min-w-0">
          {activeSection === 'platform-roles' && <PlatformRolesPanel canManage={user.identity?.platform_role === 'senior_operator'} />}
          {activeSection === 'organization-reviews' && <OrganizationReviewsPanel />}
          {activeSection === 'organization-members' && <OrganizationMembersPanel />}
          {activeSection === 'activity-collaborators' && <TopicCollaboratorsPanel suggestedTopicId={suggestedTopicId} />}
        </div>
      </div>
    </div>
  )
}
