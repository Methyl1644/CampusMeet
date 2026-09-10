import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertCircle, CheckCircle, Clock, Edit3, FileText, LogOut, Shield, Users } from 'lucide-react'
import { getProfile, updateProfile } from '@/api/auth'
import { getMyPosts } from '@/api/posts'
import { getMyApplications } from '@/api/applications'
import { getMyTeams } from '@/api/teams'
import { useAuthStore } from '@/store/authStore'
import { useToast } from '@/components/Toast'
import { COMMON_SKILLS } from '@shared/constants'
import type { Application, Post, Team, User } from '@shared/types'
import Loading from '@/components/Loading'
import EmptyState from '@/components/EmptyState'
import StatusBadge from '@/components/StatusBadge'
import { Reveal } from '@/components/motion/Reveal'

type Tab = 'posts' | 'applications' | 'teams'

export default function Profile() {
  const navigate = useNavigate()
  const { user, logout, updateUser } = useAuthStore()
  const { showToast } = useToast()

  const [profile, setProfile] = useState<User | null>(user)
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(false)
  const [activeTab, setActiveTab] = useState<Tab>('posts')
  const [posts, setPosts] = useState<Post[]>([])
  const [applications, setApplications] = useState<Application[]>([])
  const [teams, setTeams] = useState<Team[]>([])

  const [editNickname, setEditNickname] = useState('')
  const [editMajor, setEditMajor] = useState('')
  const [editGrade, setEditGrade] = useState('')
  const [editSkills, setEditSkills] = useState<string[]>([])

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      try {
        const [profileData, postsData, appsData, teamsData] = await Promise.all([
          getProfile(),
          getMyPosts(),
          getMyApplications(),
          getMyTeams(),
        ])
        setProfile(profileData)
        setPosts(postsData)
        setApplications(appsData)
        setTeams(teamsData)
      } catch {
        showToast('加载失败', 'error')
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const startEdit = () => {
    if (!profile) return
    setEditNickname(profile.nickname)
    setEditMajor(profile.major || '')
    setEditGrade(profile.grade || '')
    setEditSkills(profile.skills || [])
    setEditing(true)
  }

  const handleSave = async () => {
    try {
      const updated = await updateProfile({
        nickname: editNickname,
        major: editMajor,
        grade: editGrade,
        skills: editSkills,
      })
      setProfile(updated)
      updateUser(updated)
      showToast('资料已更新', 'success')
      setEditing(false)
    } catch {
      showToast('更新失败', 'error')
    }
  }

  const toggleSkill = (skill: string) => {
    setEditSkills((prev) =>
      prev.includes(skill) ? prev.filter((item) => item !== skill) : [...prev, skill],
    )
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  if (loading) return <Loading />
  if (!profile) return <Loading />

  return (
    <div className="mx-auto max-w-4xl">
      <Reveal as="header" className="border-y border-stone bg-paper px-4 py-5 sm:px-6">
        <div className="flex items-start gap-3 sm:gap-4">
          <div className="flex size-14 shrink-0 items-center justify-center rounded-full bg-primary-100 font-serif text-xl font-semibold text-primary-700 sm:size-16">
            {profile.nickname.charAt(0)}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="truncate font-serif text-xl font-semibold text-ink sm:text-2xl">
                {profile.nickname}
              </h1>
              {profile.auth_status !== 'unverified' && (
                <span className="inline-flex items-center gap-1 text-xs font-semibold text-campus-green">
                  <CheckCircle aria-hidden="true" size={15} />
                  {profile.auth_status === 'organization' ? '组织认证' : '校园认证'}
                </span>
              )}
            </div>
            <p className="mt-1 text-sm text-ink-muted">
              {profile.major || '暂无'} · {profile.grade || '暂无'}
            </p>
            {profile.auth_status === 'unverified' && (
              <button
                onClick={() => navigate('/login')}
                className="mt-2 inline-flex items-center gap-1.5 text-xs font-semibold text-campus-gold hover:text-amber-800"
              >
                <Shield aria-hidden="true" size={13} />
                校园认证
              </button>
            )}
          </div>
          {!editing && (
            <button onClick={startEdit} className="btn-secondary shrink-0 px-3 text-xs">
              <Edit3 aria-hidden="true" size={14} />
              <span className="hidden sm:inline">编辑资料</span>
              <span className="sm:hidden">编辑</span>
            </button>
          )}
        </div>

        {!editing && (
          <section className="mt-5 border-t border-stone pt-4" aria-labelledby="skills-title">
            <h2 id="skills-title" className="section-label">技能标签</h2>
            <div className="mt-3 flex flex-wrap gap-2">
              {profile.skills.length > 0 ? (
                profile.skills.map((skill) => (
                  <span key={skill} className="rounded-card border border-primary-200 bg-primary-50 px-2.5 py-1 text-xs font-medium text-primary-700">
                    {skill}
                  </span>
                ))
              ) : (
                <span className="text-xs text-ink-muted">暂无技能标签</span>
              )}
            </div>
          </section>
        )}

        {editing && (
          <section className="mt-5 border-t border-stone pt-4" aria-labelledby="edit-profile-title">
            <h2 id="edit-profile-title" className="section-label">编辑资料</h2>
            <div className="mt-4 space-y-4">
              <div>
                <label htmlFor="profile-nickname" className="mb-1.5 block text-xs font-semibold text-ink-muted">昵称</label>
                <input
                  id="profile-nickname"
                  type="text"
                  value={editNickname}
                  onChange={(event) => setEditNickname(event.target.value)}
                  className="input-base text-sm"
                />
              </div>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label htmlFor="profile-major" className="mb-1.5 block text-xs font-semibold text-ink-muted">专业</label>
                  <input
                    id="profile-major"
                    type="text"
                    value={editMajor}
                    onChange={(event) => setEditMajor(event.target.value)}
                    className="input-base text-sm"
                  />
                </div>
                <div>
                  <label htmlFor="profile-grade" className="mb-1.5 block text-xs font-semibold text-ink-muted">年级</label>
                  <input
                    id="profile-grade"
                    type="text"
                    value={editGrade}
                    onChange={(event) => setEditGrade(event.target.value)}
                    className="input-base text-sm"
                  />
                </div>
              </div>
              <fieldset>
                <legend className="text-xs font-semibold text-ink-muted">技能标签</legend>
                <div className="mt-2 flex flex-wrap gap-2">
                  {COMMON_SKILLS.map((skill) => (
                    <button
                      key={skill}
                      type="button"
                      onClick={() => toggleSkill(skill)}
                      aria-pressed={editSkills.includes(skill)}
                      className={`min-h-8 rounded-card border px-2.5 py-1 text-xs font-medium transition-colors ${
                        editSkills.includes(skill)
                          ? 'border-primary-600 bg-primary-50 text-primary-700'
                          : 'border-stone text-ink-muted hover:border-primary-300'
                      }`}
                    >
                      {skill}
                    </button>
                  ))}
                </div>
              </fieldset>
              <div className="grid grid-cols-2 gap-3 border-t border-stone pt-4">
                <button onClick={() => setEditing(false)} className="btn-secondary min-h-10 text-xs">
                  取消
                </button>
                <button onClick={handleSave} className="btn-primary min-h-10 text-xs">
                  保存
                </button>
              </div>
            </div>
          </section>
        )}
      </Reveal>

      <Reveal as="section" delay={0.04} className="mt-6 grid grid-cols-3 divide-x divide-stone border-y border-stone bg-paper">
        <h2 id="profile-stats-title" className="sr-only">个人数据</h2>
        <StatSummary icon={FileText} label="我的帖子" value={posts.length} />
        <StatSummary icon={Users} label="我的申请" value={applications.length} />
        <StatSummary icon={CheckCircle} label="我的团队" value={teams.length} />
      </Reveal>

      <Reveal as="section" delay={0.06} className="mt-7">
        <div role="tablist" aria-label="个人记录" className="flex min-w-0 border-b border-stone">
          <TabButton active={activeTab === 'posts'} onClick={() => setActiveTab('posts')} label="我的帖子" controls="profile-posts" />
          <TabButton active={activeTab === 'applications'} onClick={() => setActiveTab('applications')} label="我的申请" controls="profile-applications" />
          <TabButton active={activeTab === 'teams'} onClick={() => setActiveTab('teams')} label="我的团队" controls="profile-teams" />
        </div>

        {activeTab === 'posts' && (
          <div id="profile-posts" role="tabpanel">
            {posts.length === 0 ? (
              <EmptyState title="还没有发布过帖子" />
            ) : (
              <div className="divide-y divide-stone border-b border-stone">
                {posts.map((post, index) => (
                  <Reveal key={post.id} delay={Math.min(index * 0.025, 0.2)}>
                    <button
                      onClick={() => navigate(`/posts/${post.id}`)}
                      className="flex min-h-16 w-full items-center justify-between gap-4 px-1 py-3 text-left transition-colors hover:bg-paper"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-semibold text-ink">{post.title}</p>
                        <p className="mt-1 truncate text-xs text-ink-muted">
                          {post.activity_name || '暂无'} · {post.deadline || '暂无'}
                        </p>
                      </div>
                      <StatusBadge status={post.status} />
                    </button>
                  </Reveal>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'applications' && (
          <div id="profile-applications" role="tabpanel">
            {applications.length === 0 ? (
              <EmptyState title="还没有提交过申请" />
            ) : (
              <div className="divide-y divide-stone border-b border-stone">
                {applications.map((application, index) => (
                  <Reveal key={application.id} delay={Math.min(index * 0.025, 0.2)}>
                    <button
                      onClick={() => navigate(`/posts/${application.post_id}`)}
                      className="flex min-h-16 w-full items-center justify-between gap-4 px-1 py-3 text-left transition-colors hover:bg-paper"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-semibold text-ink">{application.role_wanted}</p>
                        <p className="mt-1 truncate text-xs text-ink-muted">{application.reason || '暂无'}</p>
                      </div>
                      <ApplicationStatus status={application.status} />
                    </button>
                  </Reveal>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'teams' && (
          <div id="profile-teams" role="tabpanel">
            {teams.length === 0 ? (
              <EmptyState title="还没有加入团队" />
            ) : (
              <div className="divide-y divide-stone border-b border-stone">
                {teams.map((team, index) => (
                  <Reveal key={team.id} delay={Math.min(index * 0.025, 0.2)}>
                    <button
                      onClick={() => navigate(`/teams/${team.id}`)}
                      className="flex min-h-16 w-full items-center justify-between gap-4 px-1 py-3 text-left transition-colors hover:bg-paper"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-semibold text-ink">{team.activity_name}</p>
                        <p className="mt-1 text-xs text-ink-muted">
                          {team.members.length} 人 · {team.created_at || '暂无'}
                        </p>
                      </div>
                      <Users aria-hidden="true" size={17} className="shrink-0 text-campus-green" />
                    </button>
                  </Reveal>
                ))}
              </div>
            )}
          </div>
        )}
      </Reveal>

      <button
        onClick={handleLogout}
        className="mt-7 flex min-h-11 w-full items-center justify-center gap-2 border-y border-stone text-sm font-medium text-ink-muted transition-colors hover:bg-paper hover:text-red-700"
      >
        <LogOut aria-hidden="true" size={16} />
        退出登录
      </button>
    </div>
  )
}

function StatSummary({ icon: Icon, label, value }: { icon: typeof Users; label: string; value: number }) {
  return (
    <div className="flex min-h-24 flex-col items-center justify-center px-2 py-3 text-center">
      <Icon aria-hidden="true" size={18} className="mb-1 text-campus-green" />
      <span className="text-lg font-semibold tabular-nums text-ink">{value}</span>
      <span className="text-xs text-ink-muted">{label}</span>
    </div>
  )
}

function TabButton({
  active,
  controls,
  label,
  onClick,
}: {
  active: boolean
  controls: string
  label: string
  onClick: () => void
}) {
  return (
    <button
      role="tab"
      aria-selected={active}
      aria-controls={controls}
      onClick={onClick}
      className={`min-h-11 min-w-0 flex-1 border-b-2 px-2 py-2 text-sm font-semibold transition-colors ${
        active ? 'border-primary-600 text-primary-700' : 'border-transparent text-ink-muted hover:text-primary-700'
      }`}
    >
      {label}
    </button>
  )
}

function ApplicationStatus({ status }: { status: Application['status'] }) {
  const config = {
    pending: { icon: Clock, label: '待处理', color: 'text-campus-gold' },
    accepted: { icon: CheckCircle, label: '已接受', color: 'text-campus-green' },
    rejected: { icon: AlertCircle, label: '已拒绝', color: 'text-red-700' },
  }[status]
  const Icon = config.icon
  return (
    <span className={`flex shrink-0 items-center gap-1 text-xs font-medium ${config.color}`}>
      <Icon aria-hidden="true" size={14} />
      {config.label}
    </span>
  )
}
