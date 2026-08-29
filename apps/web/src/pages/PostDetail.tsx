import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Users, Clock, MapPin, Calendar, AlertTriangle, ArrowLeft, CheckCircle } from 'lucide-react'
import { getPostDetail } from '@/api/posts'
import type { Post } from '@shared/types'
import SourceBadge from '@/components/SourceBadge'
import RiskTag from '@/components/RiskTag'
import StatusBadge from '@/components/StatusBadge'
import Loading from '@/components/Loading'
import ApplicationModal from '@/components/ApplicationModal'
import { useAuthStore } from '@/store/authStore'
import { useToast } from '@/components/Toast'

export default function PostDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const { showToast } = useToast()

  const [post, setPost] = useState<Post | null>(null)
  const [loading, setLoading] = useState(true)
  const [showApplyModal, setShowApplyModal] = useState(false)
  const [applied, setApplied] = useState(false)

  useEffect(() => {
    if (!id) return
    let cancelled = false
    const fetchPost = async () => {
      setLoading(true)
      try {
        const data = await getPostDetail(id)
        if (!cancelled) setPost(data)
      } catch {
        if (!cancelled) showToast('加载失败', 'error')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchPost()
    return () => { cancelled = true }
  }, [id]) // eslint-disable-line react-hooks/exhaustive-deps

  if (loading) return <Loading />
  if (!post) {
    return (
      <div className="py-16 text-center">
        <p className="text-sm text-gray-500">帖子不存在或已被删除</p>
        <button onClick={() => navigate('/home')} className="btn-secondary mt-4">返回首页</button>
      </div>
    )
  }

  const isAuthor = user?.id === post.author.id
  const canApply = !isAuthor && post.status === 'recruiting' && !applied
  const isUnverified = user?.auth_status === 'unverified'

  const handleApplyClick = () => {
    if (isUnverified) {
      showToast('请先完成校园邮箱认证', 'error')
      return
    }
    setShowApplyModal(true)
  }

  return (
    <div className="mx-auto max-w-2xl">
      {/* 返回按钮 */}
      <button
        onClick={() => navigate(-1)}
        className="mb-3 flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
      >
        <ArrowLeft size={16} />
        返回
      </button>

      {/* 帖子头部 */}
      <div className="card mb-3">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <SourceBadge type={post.source_type} />
          <span className="text-xs text-gray-500">{post.main_category}</span>
          <StatusBadge status={post.status} />
          {post.risk_level !== 'low' && <RiskTag level={post.risk_level} />}
        </div>

        <h1 className="mb-2 text-lg font-bold text-gray-900">{post.title}</h1>

        {/* 标签 */}
        {post.tags.length > 0 && (
          <div className="mb-3 flex flex-wrap gap-1.5">
            {post.tags.map((tag) => (
              <span key={tag} className="badge bg-gray-100 text-gray-600">
                {tag}
              </span>
            ))}
          </div>
        )}

        {/* 描述 */}
        {post.description && (
          <p className="mb-4 text-sm leading-relaxed text-gray-700">{post.description}</p>
        )}

        {/* 帖子信息网格 */}
        <div className="grid grid-cols-2 gap-3 border-t border-gray-100 pt-3">
          <InfoItem icon={Calendar} label="活动名称" value={post.activity_name} />
          <InfoItem icon={Users} label="人数" value={`${post.current_members}/${post.target_members} 人`} />
          <InfoItem icon={Clock} label="每周投入" value={post.weekly_hours} />
          <InfoItem icon={MapPin} label="组队范围" value={post.school_scope} />
          <InfoItem icon={Calendar} label="截止日期" value={post.deadline} />
        </div>

        {/* 需要角色 */}
        <div className="mt-3 border-t border-gray-100 pt-3">
          <p className="mb-1.5 text-xs font-medium text-gray-500">需要的角色</p>
          <div className="flex flex-wrap gap-2">
            {post.needed_roles.map((role) => (
              <span key={role} className="rounded-lg bg-primary-50 px-3 py-1 text-sm font-medium text-primary-600">
                {role}
              </span>
            ))}
          </div>
        </div>

        {/* 风险提示 */}
        {post.risk_level !== 'low' && (
          <div className="mt-3 flex items-start gap-2 rounded-lg bg-orange-50 p-3">
            <AlertTriangle size={16} className="mt-0.5 text-orange-500" />
            <p className="text-xs text-orange-700">
              {post.risk_level === 'high'
                ? '该活动被标记为高风险，请注意人身和财产安全。如有疑问请联系平台。'
                : '该活动涉及线下/夜间等场景，请注意安全。'}
            </p>
          </div>
        )}
      </div>

      {/* 匹配推荐 */}
      {post.match_score !== undefined && (
        <div className="card mb-3 border-primary-200 bg-primary-50">
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold text-primary-600">{post.match_score}%</span>
            <span className="text-sm text-primary-600">匹配度</span>
          </div>
          {post.match_reason && (
            <p className="mt-1 text-xs text-primary-700">{post.match_reason}</p>
          )}
        </div>
      )}

      {/* 发帖者信息 */}
      <div className="card mb-3">
        <p className="mb-2 text-xs font-medium text-gray-500">发布者</p>
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary-100 text-sm font-medium text-primary-600">
            {post.author.nickname.charAt(0)}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-900">{post.author.nickname}</span>
              {post.author.auth_status !== 'unverified' && (
                <CheckCircle size={14} className="text-green-500" />
              )}
            </div>
            <p className="text-xs text-gray-500">
              {post.author.major} · {post.author.grade}
            </p>
          </div>
        </div>
      </div>

      {/* 操作区 */}
      <div className="sticky bottom-16 md:bottom-0">
        {isAuthor ? (
          <div className="rounded-xl border border-gray-200 bg-white p-3 text-center text-sm text-gray-500">
            这是你发布的帖子
          </div>
        ) : applied ? (
          <div className="flex items-center justify-center gap-2 rounded-xl border border-green-200 bg-green-50 p-3 text-sm text-green-600">
            <CheckCircle size={16} />
            已申请，等待回复
          </div>
        ) : canApply ? (
          <button onClick={handleApplyClick} className="btn-primary w-full py-3">
            申请加入
          </button>
        ) : (
          <div className="rounded-xl border border-gray-200 bg-gray-50 p-3 text-center text-sm text-gray-400">
            {post.status === 'full' ? '已满员' : post.status === 'expired' ? '已截止' : '不可申请'}
          </div>
        )}
      </div>

      {/* 申请弹窗 */}
      {showApplyModal && post && (
        <ApplicationModal
          post={post}
          onClose={() => setShowApplyModal(false)}
          onSuccess={() => setApplied(true)}
        />
      )}
    </div>
  )
}

function InfoItem({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Users
  label: string
  value: string
}) {
  return (
    <div className="flex items-start gap-2">
      <Icon size={16} className="mt-0.5 text-gray-400" />
      <div>
        <p className="text-xs text-gray-400">{label}</p>
        <p className="text-sm text-gray-800">{value}</p>
      </div>
    </div>
  )
}
