import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Edit3, CheckCircle, Clock, AlertCircle, Users, FileText, LogOut, Shield, Plus } from 'lucide-react'
import { getProfile, updateProfile } from '@/api/auth'
import { getMyPosts } from '@/api/posts'
import { getMyApplications } from '@/api/applications'
import { getMyTeams } from '@/api/teams'
import { useAuthStore } from '@/store/authStore'
import { useToast } from '@/components/Toast'
import { COMMON_SKILLS } from '@shared/constants'
import type { Post, Application, Team, User } from '@shared/types'
import Loading from '@/components/Loading'
import EmptyState from '@/components/EmptyState'
import StatusBadge from '@/components/StatusBadge'

type Tab = 'posts' | 'applications' | 'teams'

export default function Profile() {
  const navigate = useNavigate()
  const { user, token, logout, updateUser } = useAuthStore()
  const { showToast } = useToast()

  const [profile, setProfile] = useState<User | null>(user)
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(false)
  const [activeTab, setActiveTab] = useState<Tab>('posts')
  const [posts, setPosts] = useState<Post[]>([])
  const [applications, setApplications] = useState<Application[]>([])
  const [teams, setTeams] = useState<Team[]>([])

  // 编辑表单
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
      prev.includes(skill) ? prev.filter((s) => s !== skill) : [...prev, skill],
    )
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  if (loading) return <Loading />
  if (!profile) return <Loading />

  return (
    <div className="mx-auto max-w-2xl">
      {/* 用户信息卡片 */}
      <div className="card mb-4">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-4">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary-100 text-xl font-bold text-primary-600">
              {profile.nickname.charAt(0)}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-bold text-gray-900">{profile.nickname}</h1>
                {profile.auth_status !== 'unverified' && (
                  <CheckCircle size={16} className="text-green-500" />
                )}
              </div>
              <p className="text-sm text-gray-500">
                {profile.major} · {profile.grade}
              </p>
              {profile.auth_status === 'unverified' && (
                <button
                  onClick={() => navigate('/login')}
                  className="mt-1 flex items-center gap-1 text-xs text-orange-500"
                >
                  <Shield size={12} />
                  点击完成校园邮箱认证
                </button>
              )}
            </div>
          </div>
          {!editing && (
            <button onClick={startEdit} className="btn-secondary text-xs">
              <Edit3 size={14} />
              编辑
            </button>
          )}
        </div>

        {/* 技能标签 */}
        {!editing && (
          <div className="mt-4 border-t border-gray-100 pt-3">
            <p className="mb-2 text-xs font-medium text-gray-500">技能标签</p>
            <div className="flex flex-wrap gap-1.5">
              {profile.skills.length > 0 ? (
                profile.skills.map((skill) => (
                  <span key={skill} className="badge bg-primary-50 text-primary-600">
                    {skill}
                  </span>
                ))
              ) : (
                <span className="text-xs text-gray-400">暂无技能标签</span>
              )}
            </div>
          </div>
        )}

        {/* 编辑模式 */}
        {editing && (
          <div className="mt-4 space-y-3 border-t border-gray-100 pt-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-500">昵称</label>
              <input
                type="text"
                value={editNickname}
                onChange={(e) => setEditNickname(e.target.value)}
                className="input-base text-sm"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-500">专业</label>
                <input
                  type="text"
                  value={editMajor}
                  onChange={(e) => setEditMajor(e.target.value)}
                  className="input-base text-sm"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-500">年级</label>
                <input
                  type="text"
                  value={editGrade}
                  onChange={(e) => setEditGrade(e.target.value)}
                  className="input-base text-sm"
                />
              </div>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-500">技能标签</label>
              <div className="flex flex-wrap gap-1.5">
                {COMMON_SKILLS.map((skill) => (
                  <button
                    key={skill}
                    onClick={() => toggleSkill(skill)}
                    className={`rounded-full border px-2.5 py-0.5 text-xs transition-colors ${
                      editSkills.includes(skill)
                        ? 'border-primary-500 bg-primary-50 text-primary-600'
                        : 'border-gray-300 text-gray-600'
                    }`}
                  >
                    {skill}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex gap-2">
              <button onClick={() => setEditing(false)} className="btn-secondary flex-1 text-xs">
                取消
              </button>
              <button onClick={handleSave} className="btn-primary flex-1 text-xs">
                保存
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 统计数据 */}
      <div className="mb-4 grid grid-cols-3 gap-3">
        <StatCard icon={FileText} label="我的帖子" value={posts.length} />
        <StatCard icon={Users} label="我的申请" value={applications.length} />
        <StatCard icon={CheckCircle} label="我的团队" value={teams.length} />
      </div>

      {/* Tab 切换 */}
      <div className="mb-3 flex gap-1 border-b border-gray-200">
        <TabButton active={activeTab === 'posts'} onClick={() => setActiveTab('posts')} label="我的帖子" />
        <TabButton active={activeTab === 'applications'} onClick={() => setActiveTab('applications')} label="我的申请" />
        <TabButton active={activeTab === 'teams'} onClick={() => setActiveTab('teams')} label="我的团队" />
      </div>

      {/* 列表内容 */}
      {activeTab === 'posts' && (
        <div className="space-y-2">
          {posts.length === 0 ? (
            <EmptyState title="还没有发布过帖子" />
          ) : (
            posts.map((post) => (
              <button
                key={post.id}
                onClick={() => navigate(`/posts/${post.id}`)}
                className="card flex w-full items-center justify-between text-left hover:shadow-md"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-gray-900">{post.title}</p>
                  <p className="text-xs text-gray-500">{post.activity_name} · {post.deadline}</p>
                </div>
                <StatusBadge status={post.status} />
              </button>
            ))
          )}
        </div>
      )}

      {activeTab === 'applications' && (
        <div className="space-y-2">
          {applications.length === 0 ? (
            <EmptyState title="还没有提交过申请" />
          ) : (
            applications.map((app) => (
              <button
                key={app.id}
                onClick={() => navigate(`/posts/${app.post_id}`)}
                className="card flex w-full items-center justify-between text-left hover:shadow-md"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-gray-900">{app.role_wanted}</p>
                  <p className="truncate text-xs text-gray-500">{app.reason}</p>
                </div>
                <ApplicationStatus status={app.status} />
              </button>
            ))
          )}
        </div>
      )}

      {activeTab === 'teams' && (
        <div className="space-y-2">
          {teams.length === 0 ? (
            <EmptyState title="还没有加入团队" />
          ) : (
            teams.map((team) => (
              <button
                key={team.id}
                onClick={() => navigate(`/teams/${team.id}`)}
                className="card flex w-full items-center justify-between text-left hover:shadow-md"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-gray-900">{team.activity_name}</p>
                  <p className="text-xs text-gray-500">{team.members.length} 人 · {team.created_at}</p>
                </div>
                <Users size={16} className="text-gray-400" />
              </button>
            ))
          )}
        </div>
      )}

      {/* 退出登录 */}
      <button
        onClick={handleLogout}
        className="mt-6 flex w-full items-center justify-center gap-2 rounded-xl border border-gray-200 py-3 text-sm text-gray-500 hover:bg-gray-50"
      >
        <LogOut size={16} />
        退出登录
      </button>
    </div>
  )
}

function StatCard({ icon: Icon, label, value }: { icon: typeof Users; label: string; value: number }) {
  return (
    <div className="card flex flex-col items-center py-3">
      <Icon size={20} className="mb-1 text-primary-600" />
      <span className="text-lg font-bold text-gray-900">{value}</span>
      <span className="text-xs text-gray-500">{label}</span>
    </div>
  )
}

function TabButton({ active, onClick, label }: { active: boolean; onClick: () => void; label: string }) {
  return (
    <button
      onClick={onClick}
      className={`border-b-2 px-3 py-2 text-sm font-medium transition-colors ${
        active ? 'border-primary-600 text-primary-600' : 'border-transparent text-gray-500'
      }`}
    >
      {label}
    </button>
  )
}

function ApplicationStatus({ status }: { status: Application['status'] }) {
  const config = {
    pending: { icon: Clock, label: '待处理', color: 'text-orange-500' },
    accepted: { icon: CheckCircle, label: '已接受', color: 'text-green-500' },
    rejected: { icon: AlertCircle, label: '已拒绝', color: 'text-red-500' },
  }[status]
  const Icon = config.icon
  return (
    <span className={`flex items-center gap-1 text-xs ${config.color}`}>
      <Icon size={14} />
      {config.label}
    </span>
  )
}
