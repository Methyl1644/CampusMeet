import { useEffect, useState } from 'react'
import {
  ArrowLeft,
  Bookmark,
  Building2,
  ExternalLink,
  FileText,
  Plus,
  ShieldCheck,
  UsersRound,
} from 'lucide-react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { getTopic, getTopicPosts, toggleTopicFollow } from '@/api/content'
import EmptyState from '@/components/EmptyState'
import Loading from '@/components/Loading'
import { Reveal } from '@/components/motion/Reveal'
import PostCard from '@/components/PostCard'
import { useToast } from '@/components/Toast'
import type { Post, Topic } from '@shared/types'

export default function TopicDetail() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const { showToast } = useToast()
  const shouldReduceMotion = useReducedMotion()
  const [topic, setTopic] = useState<Topic | null>(null)
  const [posts, setPosts] = useState<Post[]>([])
  const [loading, setLoading] = useState(true)
  const [following, setFollowing] = useState(false)

  useEffect(() => {
    let cancelled = false
    Promise.all([getTopic(id), getTopicPosts(id)])
      .then(([topicResult, postResult]) => {
        if (!cancelled) {
          setTopic(topicResult)
          setPosts(postResult)
        }
      })
      .catch(() => {
        if (!cancelled) showToast('话题加载失败', 'error')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [id, showToast])

  if (loading) return <Loading />
  if (!topic)
    return (
      <EmptyState title="话题不存在" />
    )

  const handleFollow = async () => {
    setFollowing(true)
    try {
      const result = await toggleTopicFollow(topic.id)
      setTopic({
        ...topic,
        followed: result.followed,
        follower_count: result.follower_count,
      })
    } catch {
      showToast('关注状态更新失败', 'error')
    } finally {
      setFollowing(false)
    }
  }

  return (
    <div className="mx-auto min-w-0 max-w-5xl overflow-x-clip">
      <button
        type="button"
        onClick={() => navigate(-1)}
        className="mb-4 inline-flex items-center gap-1 text-sm font-medium text-ink-muted transition-colors hover:text-primary-700"
      >
        <ArrowLeft aria-hidden="true" className="size-4" />返回
      </button>

      <Reveal
        as="header"
        className="border-y border-stone bg-paper px-4 py-5 sm:px-6 sm:py-7"
      >
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2 border-b border-stone pb-4 text-xs text-ink-muted">
          <span className="inline-flex items-center gap-1.5 font-semibold text-campus-green">
            <ShieldCheck aria-hidden="true" className="size-4" />
            {topic.channel === 'official' ? '官方话题' : '认证组织话题'}
          </span>
          <span>{topic.edition}</span>
          <span className="inline-flex min-w-0 items-center gap-1.5">
            <Building2 aria-hidden="true" className="size-3.5 shrink-0" />
            {topic.organizer}
          </span>
          <span className="sm:ml-auto">{topic.source_status}</span>
        </div>

        <div className="mt-5 flex flex-col justify-between gap-5 md:flex-row md:items-start">
          <div className="min-w-0 max-w-3xl">
            <h1 className="text-2xl font-semibold leading-9 text-ink sm:text-3xl sm:leading-10">
              {topic.title}
            </h1>
            <p className="mt-3 text-sm leading-7 text-ink-muted">
              {topic.summary}
            </p>

            <div className="mt-4 flex flex-wrap gap-2" aria-label="标准标签">
              {topic.tags.map((tag) => (
                <span key={tag.tag_id} className="tag-chip">
                  <span
                    className="size-2 shrink-0 rounded-full border border-black/10"
                    style={{ backgroundColor: tag.display_color }}
                  />
                  {tag.canonical_name}
                </span>
              ))}
            </div>

            {topic.source_url && (
              <a
                href={topic.source_url}
                target="_blank"
                rel="noreferrer"
                className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-primary-700 hover:underline"
              >
                查看原始来源
                <ExternalLink aria-hidden="true" className="size-3.5" />
              </a>
            )}
          </div>

          <div className="flex shrink-0 items-center gap-2">
            <button
              type="button"
              disabled={following}
              onClick={handleFollow}
              className={`${topic.followed ? 'btn-secondary' : 'btn-primary'} min-w-32`}
              aria-live="polite"
            >
              <Bookmark
                aria-hidden="true"
                className="size-4"
                fill={topic.followed ? 'currentColor' : 'none'}
              />
              <AnimatePresence mode="wait" initial={false}>
                <motion.span
                  key={`${topic.followed}-${topic.follower_count}`}
                  initial={shouldReduceMotion ? false : { opacity: 0, y: 3 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: -3 }}
                  transition={{ duration: shouldReduceMotion ? 0 : 0.18 }}
                >
                  {topic.followed ? '已关注' : '关注'} · {topic.follower_count}
                </motion.span>
              </AnimatePresence>
            </button>
            <Link
              to={`/publish?kind=topic_team&topic_id=${topic.id}`}
              className="btn-primary hidden sm:inline-flex"
            >
              <Plus aria-hidden="true" className="size-4" />发起组队
            </Link>
          </div>
        </div>
      </Reveal>

      <div className="grid gap-7 py-7 lg:grid-cols-[minmax(0,1fr)_240px] lg:gap-10">
        <Reveal as="main" delay={0.04}>
          <div className="flex items-center gap-2 border-b border-stone pb-3">
            <FileText aria-hidden="true" className="size-4 text-campus-green" />
            <h2 className="text-lg font-semibold text-ink">活动资料</h2>
          </div>
          <div className="mt-4 whitespace-pre-wrap text-sm leading-7 text-ink">
            {topic.content}
          </div>
        </Reveal>

        <Reveal
          as="aside"
          className="border-t border-stone pt-5 lg:border-l lg:border-t-0 lg:pl-6 lg:pt-0"
          delay={0.08}
        >
          <p className="section-label">话题档案</p>
          <dl className="mt-4 grid gap-4 text-sm">
            <div>
              <dt className="text-xs text-ink-muted">主办方</dt>
              <dd className="mt-1 font-medium text-ink">{topic.organizer}</dd>
            </div>
            <div>
              <dt className="text-xs text-ink-muted">届次</dt>
              <dd className="mt-1 font-medium text-ink">{topic.edition}</dd>
            </div>
            <div>
              <dt className="text-xs text-ink-muted">来源状态</dt>
              <dd className="mt-1 font-medium text-campus-green">
                {topic.source_status}
              </dd>
            </div>
          </dl>
          <div className="mt-5 flex items-center gap-2 border-t border-stone pt-4 text-sm text-ink-muted">
            <UsersRound aria-hidden="true" className="size-4 text-campus-green" />
            当前 {posts.length} 条招募
          </div>
        </Reveal>
      </div>

      <Reveal
        as="section"
        className="border-t border-stone pt-6"
        delay={0.1}
      >
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="section-label">加入活动</p>
            <h2 className="mt-2 text-xl font-semibold text-ink">相关组队帖</h2>
          </div>
          <Link
            to={`/publish?kind=topic_team&topic_id=${topic.id}`}
            className="btn-primary"
          >
            <Plus aria-hidden="true" className="size-4" />发布招募
          </Link>
        </div>

        {posts.length > 0 ? (
          <div className="grid gap-4 md:grid-cols-2">
            {posts.map((post, index) => (
              <Reveal
                key={post.id}
                as="article"
                className="h-full min-w-0"
                delay={Math.min(index * 0.035, 0.35)}
              >
                <PostCard post={post} />
              </Reveal>
            ))}
          </div>
        ) : (
          <EmptyState title="还没有组队帖" />
        )}
      </Reveal>
    </div>
  )
}
