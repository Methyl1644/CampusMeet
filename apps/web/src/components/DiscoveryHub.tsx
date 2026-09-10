import { useCallback, useEffect, useRef, useState } from 'react'
import {
  ArrowRight,
  BadgeCheck,
  Landmark,
  Search,
  UsersRound,
  X,
} from 'lucide-react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { useNavigate } from 'react-router-dom'

import { getSearchSuggestions, getTopics } from '@/api/content'
import { getPosts } from '@/api/posts'
import EmptyState from '@/components/EmptyState'
import Loading from '@/components/Loading'
import { Reveal } from '@/components/motion/Reveal'
import PostCard from '@/components/PostCard'
import TopicCard from '@/components/TopicCard'
import { useToast } from '@/components/Toast'
import type {
  ContentChannel,
  Post,
  SearchDirectResult,
  StandardTag,
  Topic,
} from '@shared/types'

const channels: Array<{ key: ContentChannel; title: string; subtitle: string }> = [
  { key: 'official', title: '官方赛事与项目', subtitle: '权威来源收录' },
  { key: 'organization', title: '认证组织活动', subtitle: '学院与社团发布' },
  { key: 'casual', title: '同学自主组队', subtitle: '运动、约饭与出游' },
]

const channelIcons = {
  official: Landmark,
  organization: BadgeCheck,
  casual: UsersRound,
} satisfies Record<ContentChannel, typeof Landmark>

export default function DiscoveryHub() {
  const navigate = useNavigate()
  const { showToast } = useToast()
  const shouldReduceMotion = useReducedMotion()
  const [channel, setChannel] = useState<ContentChannel>('official')
  const [query, setQuery] = useState('')
  const [selectedTags, setSelectedTags] = useState<StandardTag[]>([])
  const [direct, setDirect] = useState<SearchDirectResult[]>([])
  const [tagSuggestions, setTagSuggestions] = useState<StandardTag[]>([])
  const [topics, setTopics] = useState<Topic[]>([])
  const [posts, setPosts] = useState<Post[]>([])
  const [loading, setLoading] = useState(true)
  const [suggesting, setSuggesting] = useState(false)
  const loadRequestId = useRef(0)
  const requestId = useRef(0)

  const load = useCallback(async (currentLoad: number) => {
    setLoading(true)
    try {
      if (channel === 'casual') {
        const response = await getPosts({
          keyword: query || undefined,
          tags: selectedTags.map((tag) => tag.tag_id),
          kind: 'casual_invitation',
          page: 1,
          page_size: 30,
        })
        if (currentLoad === loadRequestId.current) {
          setPosts(response.list)
          setTopics([])
        }
      } else {
        const response = await getTopics({
          channel,
          q: query || undefined,
          tag_ids: selectedTags.map((tag) => tag.tag_id),
          page: 1,
          page_size: 30,
        })
        if (currentLoad === loadRequestId.current) {
          setTopics(response.list)
          setPosts([])
        }
      }
    } catch {
      if (currentLoad === loadRequestId.current) {
        setTopics([])
        setPosts([])
        showToast('内容加载失败，请确认后端服务已启动', 'error')
      }
    } finally {
      if (currentLoad === loadRequestId.current) setLoading(false)
    }
  }, [channel, query, selectedTags, showToast])

  useEffect(() => {
    const currentLoad = ++loadRequestId.current
    const timer = window.setTimeout(() => load(currentLoad), 250)
    return () => window.clearTimeout(timer)
  }, [load])

  useEffect(() => {
    const trimmed = query.trim()
    if (!trimmed) {
      setDirect([])
      setTagSuggestions([])
      setSuggesting(false)
      return
    }
    const current = ++requestId.current
    const timer = window.setTimeout(async () => {
      setSuggesting(true)
      try {
        const response = await getSearchSuggestions(trimmed, channel)
        if (current === requestId.current) {
          setDirect(response.direct)
          setTagSuggestions(
            response.tags.filter(
              (tag) =>
                !selectedTags.some(
                  (selected) => selected.tag_id === tag.tag_id,
                ),
            ),
          )
        }
      } catch {
        if (current === requestId.current) {
          setDirect([])
          setTagSuggestions([])
        }
      } finally {
        if (current === requestId.current) setSuggesting(false)
      }
    }, 180)
    return () => window.clearTimeout(timer)
  }, [channel, query, selectedTags])

  return (
    <div className="min-w-0 overflow-x-clip">
      <Reveal
        as="header"
        className="grid grid-cols-[minmax(0,1fr)_64px] items-center gap-4 border-b border-stone pb-5 md:grid-cols-[minmax(0,1fr)_84px] md:pb-7"
      >
        <div className="min-w-0">
          <p className="section-label">南京大学校内组队</p>
          <h1 className="mt-3 text-2xl font-semibold leading-9 text-ink md:text-3xl">
            找到活动，也找到一起出发的人
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-ink-muted">
            正式赛事先查看话题资料，日常邀约直接联系发起人。
          </p>
        </div>
        <img
          src="/campus-clocktower-badge.jpg"
          alt="南京大学校园钟楼圆章"
          className="aspect-square w-full rounded-card border border-stone object-cover shadow-panel"
        />
      </Reveal>

      <nav
        className="grid grid-cols-3 border-b border-stone"
        role="tablist"
        aria-label="内容频道"
      >
        {channels.map((item) => {
          const Icon = channelIcons[item.key]
          const active = channel === item.key

          return (
            <button
              key={item.key}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => {
                setChannel(item.key)
                setQuery('')
                setSelectedTags([])
              }}
              className={`relative flex min-w-0 items-center justify-center gap-2 px-1 py-4 text-center transition-colors sm:px-3 md:min-h-20 ${
                active
                  ? 'text-ink'
                  : 'text-ink-muted hover:text-primary-700'
              }`}
            >
              <Icon
                aria-hidden="true"
                className={`hidden size-5 shrink-0 sm:block ${active ? 'text-primary-600' : ''}`}
              />
              <span className="min-w-0">
                <span className="block text-xs font-semibold leading-5 sm:text-sm">
                  {item.title}
                </span>
                <span className="mt-0.5 hidden text-xs text-ink-muted md:block">
                  {item.subtitle}
                </span>
              </span>
              {active && (
                <motion.span
                  layoutId="discovery-channel-underline"
                  className="absolute inset-x-2 bottom-0 h-0.5 bg-primary-600 sm:inset-x-4"
                  transition={
                    shouldReduceMotion
                      ? { duration: 0 }
                      : { duration: 0.22, ease: [0.22, 1, 0.36, 1] }
                  }
                />
              )}
            </button>
          )
        })}
      </nav>

      <Reveal as="section" className="py-5 md:py-6" delay={0.04}>
        <div className="relative mx-auto max-w-3xl">
          <Search
            className="pointer-events-none absolute left-4 top-3.5 size-4 text-ink-muted"
            aria-hidden="true"
          />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            className="input-base h-11 pl-11 pr-11 shadow-panel"
            placeholder={
              channel === 'casual'
                ? '搜索活动、地点或标准标签'
                : '搜索赛事名称、简称或标准标签'
            }
            aria-label="搜索话题和标签"
          />
          {query && (
            <button
              type="button"
              onClick={() => setQuery('')}
              className="icon-button absolute right-0.5 top-0.5 size-10"
              aria-label="清空搜索"
              title="清空搜索"
            >
              <X aria-hidden="true" className="size-4" />
            </button>
          )}

          <AnimatePresence>
            {query &&
              (suggesting ||
                direct.length > 0 ||
                tagSuggestions.length > 0) && (
                <motion.div
                  className="absolute left-0 right-0 top-12 z-30 overflow-hidden rounded-card border border-stone bg-paper shadow-lg"
                  initial={
                    shouldReduceMotion
                      ? false
                      : { opacity: 0, scale: 0.98, y: -4 }
                  }
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={
                    shouldReduceMotion
                      ? { opacity: 0 }
                      : { opacity: 0, scale: 0.98, y: -4 }
                  }
                  transition={{ duration: shouldReduceMotion ? 0 : 0.16 }}
                >
                  {suggesting ? (
                    <p className="px-4 py-3 text-sm text-ink-muted">
                      正在查找...
                    </p>
                  ) : (
                    <>
                      {direct.length > 0 && (
                        <div className="border-b border-stone py-1">
                          <p className="px-4 pb-1 pt-2 text-xs font-semibold text-campus-green">
                            话题直达
                          </p>
                          {direct.map((item) => (
                            <button
                              type="button"
                              key={`${item.entity_type}-${item.entity_id}`}
                              onClick={() =>
                                navigate(`/topics/${item.entity_id}`)
                              }
                              className="flex w-full items-center justify-between gap-3 px-4 py-2.5 text-left transition-colors hover:bg-primary-50"
                            >
                              <span className="min-w-0">
                                <span className="block truncate text-sm font-semibold text-ink">
                                  {item.title}
                                </span>
                                <span className="block truncate text-xs text-ink-muted">
                                  {item.subtitle}
                                </span>
                              </span>
                              <ArrowRight
                                aria-hidden="true"
                                className="size-4 shrink-0 text-primary-600"
                              />
                            </button>
                          ))}
                        </div>
                      )}
                      {tagSuggestions.length > 0 && (
                        <div className="py-1">
                          <p className="px-4 pb-1 pt-2 text-xs font-semibold text-ink-muted">
                            标准标签
                          </p>
                          {tagSuggestions.map((tag) => (
                            <button
                              type="button"
                              key={tag.tag_id}
                              onClick={() => {
                                setSelectedTags((currentTags) => [
                                  ...currentTags,
                                  tag,
                                ])
                                setQuery('')
                              }}
                              className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm transition-colors hover:bg-primary-50"
                            >
                              <span
                                className="size-2.5 shrink-0 rounded-full border border-black/10"
                                style={{ backgroundColor: tag.display_color }}
                              />
                              <span className="font-medium text-ink">
                                {tag.canonical_name}
                              </span>
                              {tag.matched_alias && (
                                <span className="min-w-0 truncate text-xs text-ink-muted">
                                  由“{tag.matched_alias}”匹配
                                </span>
                              )}
                            </button>
                          ))}
                        </div>
                      )}
                    </>
                  )}
                </motion.div>
              )}
          </AnimatePresence>
        </div>

        {selectedTags.length > 0 && (
          <div
            className="mx-auto mt-3 flex max-w-3xl flex-wrap items-center gap-2"
            aria-label="已选择标签"
          >
            {selectedTags.map((tag) => (
              <span key={tag.tag_id} className="tag-chip">
                <span
                  className="size-2 shrink-0 rounded-full border border-black/10"
                  style={{ backgroundColor: tag.display_color }}
                />
                {tag.canonical_name}
                <button
                  type="button"
                  onClick={() =>
                    setSelectedTags((items) =>
                      items.filter((item) => item.tag_id !== tag.tag_id),
                    )
                  }
                  className="ml-0.5 inline-flex size-5 items-center justify-center rounded-full text-primary-700 transition-colors hover:bg-primary-200"
                  aria-label={`移除${tag.canonical_name}`}
                  title={`移除${tag.canonical_name}`}
                >
                  <X aria-hidden="true" className="size-3.5" />
                </button>
              </span>
            ))}
          </div>
        )}
      </Reveal>

      <AnimatePresence mode="wait" initial={false}>
        <motion.section
          key={channel}
          aria-live="polite"
          initial={shouldReduceMotion ? false : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: -4 }}
          transition={{ duration: shouldReduceMotion ? 0 : 0.22 }}
        >
          {loading ? (
            <Loading />
          ) : channel === 'casual' ? (
            posts.length > 0 ? (
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
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
              <EmptyState
                title="暂时没有匹配的自主组队"
                description="调整关键词，或发布一条新的日常邀约"
              />
            )
          ) : topics.length > 0 ? (
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {topics.map((topic, index) => (
                <Reveal
                  key={topic.id}
                  as="article"
                  className="h-full min-w-0"
                  delay={Math.min(index * 0.035, 0.35)}
                >
                  <TopicCard topic={topic} />
                </Reveal>
              ))}
            </div>
          ) : (
            <EmptyState
              title="暂时没有匹配的话题"
              description="试试活动简称或标准标签"
            />
          )}
        </motion.section>
      </AnimatePresence>
    </div>
  )
}
