import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  Calendar,
  CheckCircle,
  Clock,
  MapPin,
  Sparkles,
  Users,
} from 'lucide-react'
import { getPostDetail } from '@/api/posts'
import type { Post } from '@shared/types'
import SourceBadge from '@/components/SourceBadge'
import RiskTag from '@/components/RiskTag'
import StatusBadge from '@/components/StatusBadge'
import Loading from '@/components/Loading'
import ApplicationModal from '@/components/ApplicationModal'
import { Reveal } from '@/components/motion/Reveal'
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
        <p className="text-sm text-ink-muted">帖子不存在或已被删除</p>
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
    <div className="mx-auto max-w-5xl">
      <button
        onClick={() => navigate(-1)}
        className="mb-4 inline-flex items-center gap-1 text-sm font-medium text-ink-muted transition-colors hover:text-primary-700"
      >
        <ArrowLeft aria-hidden="true" size={16} />
        返回
      </button>

      <Reveal as="article" className="border-y border-stone bg-paper px-4 py-6 sm:px-7 sm:py-8">
        <header className="border-b border-stone pb-6">
          <div className="flex flex-wrap items-center gap-2">
            <SourceBadge type={post.source_type} />
            <span className="text-xs font-medium text-ink-muted">{post.main_category}</span>
            <StatusBadge status={post.status} />
            {post.risk_level !== 'low' && <RiskTag level={post.risk_level} />}
          </div>

          <h1 id="post-title" className="mt-4 font-serif text-2xl font-semibold leading-9 text-ink sm:text-3xl sm:leading-10">
            {post.title}
          </h1>
          <p className="mt-4 whitespace-pre-wrap text-sm leading-7 text-ink-muted">
            {post.description || '暂无'}
          </p>

          {post.tags.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-2" aria-label="帖子标签">
              {post.tags.map((tag) => (
                <span key={tag} className="badge border border-stone bg-paper-warm text-ink-muted">
                  {tag}
                </span>
              ))}
            </div>
          )}
        </header>

        <div className="grid gap-7 pt-6 lg:grid-cols-[minmax(0,1fr)_17rem] lg:gap-10">
          <main className="min-w-0 space-y-7">
            <section aria-labelledby="conditions-title">
              <SectionTitle id="conditions-title">招募条件</SectionTitle>
              <dl className="mt-4 grid grid-cols-1 gap-x-6 gap-y-4 sm:grid-cols-2">
                <InfoItem icon={Calendar} label="活动名称" value={post.activity_name || '暂无'} />
                <InfoItem icon={Users} label="人数" value={`${post.current_members}/${post.target_members} 人`} />
                <InfoItem icon={Clock} label="每周投入" value={post.weekly_hours || '暂无'} />
                <InfoItem icon={MapPin} label="组队范围" value={post.school_scope || '暂无'} />
                <InfoItem icon={Calendar} label="截止日期" value={post.deadline || '暂无'} />
              </dl>
            </section>

            <section className="border-t border-stone pt-6" aria-labelledby="roles-title">
              <SectionTitle id="roles-title">所需角色</SectionTitle>
              {post.needed_roles.length > 0 ? (
                <div className="mt-4 flex flex-wrap gap-2">
                  {post.needed_roles.map((role) => (
                    <span key={role} className="rounded-card border border-primary-200 bg-primary-50 px-3 py-1.5 text-sm font-semibold text-primary-700">
                      {role}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="mt-3 text-sm text-ink-muted">暂无</p>
              )}
            </section>

            {post.match_score !== undefined && (
              <section className="border-t border-stone pt-6" aria-labelledby="match-title">
                <div className="flex items-center gap-2 text-primary-700">
                  <Sparkles aria-hidden="true" size={16} />
                  <h2 id="match-title" className="text-sm font-semibold">AI 匹配说明</h2>
                  <span className="ml-auto text-sm font-semibold tabular-nums">{post.match_score}%</span>
                </div>
                <p className="mt-2 text-xs leading-6 text-ink-muted">
                  {post.match_reason || '暂无'}
                </p>
              </section>
            )}
          </main>

          <aside className="border-t border-stone pt-6 lg:border-l lg:border-t-0 lg:pl-7 lg:pt-0" aria-labelledby="author-title">
            <SectionTitle id="author-title">发起人</SectionTitle>
            <div className="mt-4 flex items-center gap-3">
              <div className="flex size-11 shrink-0 items-center justify-center rounded-full bg-primary-100 text-sm font-semibold text-primary-700">
                {post.author.nickname.charAt(0)}
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="truncate text-sm font-semibold text-ink">{post.author.nickname}</span>
                  {post.author.auth_status !== 'unverified' && (
                    <CheckCircle aria-label="已认证" size={15} className="shrink-0 text-campus-green" />
                  )}
                </div>
                <p className="mt-1 text-xs text-ink-muted">
                  {post.author.major || '暂无'} · {post.author.grade || '暂无'}
                </p>
              </div>
            </div>
          </aside>
        </div>
      </Reveal>

      <Reveal
        as="footer"
        delay={0.04}
        className="sticky bottom-[calc(4.75rem+env(safe-area-inset-bottom))] z-20 mt-4 border border-stone bg-paper/95 p-3 shadow-panel md:bottom-3"
      >
        {isAuthor ? (
          <div className="min-h-11 content-center text-center text-sm text-ink-muted">
            这是你发布的帖子
          </div>
        ) : applied ? (
          <div className="flex min-h-11 items-center justify-center gap-2 text-sm font-medium text-campus-green">
            <CheckCircle aria-hidden="true" size={16} />
            已申请，等待回复
          </div>
        ) : canApply ? (
          <button onClick={handleApplyClick} className="btn-primary min-h-11 w-full">
            申请加入
          </button>
        ) : (
          <div className="min-h-11 content-center text-center text-sm text-ink-muted">
            {post.status === 'full' ? '已满员' : post.status === 'expired' ? '已截止' : '不可申请'}
          </div>
        )}
      </Reveal>

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

function SectionTitle({ id, children }: { id: string; children: string }) {
  return <h2 id={id} className="section-label">{children}</h2>
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
    <div className="flex min-h-12 items-start gap-3 border-b border-stone/70 pb-3">
      <Icon aria-hidden="true" size={16} className="mt-1 shrink-0 text-campus-green" />
      <div className="min-w-0">
        <dt className="text-xs text-ink-muted">{label}</dt>
        <dd className="mt-1 break-words text-sm font-medium text-ink">{value}</dd>
      </div>
    </div>
  )
}
