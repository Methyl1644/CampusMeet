import { useEffect, useRef, useState } from 'react'
import { Check, Edit3, RefreshCw, Send, Sparkles, X } from 'lucide-react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { postDraft } from '@/api/agent'
import { createPost } from '@/api/posts'
import { AIThinking } from '@/components/Loading'
import { Reveal } from '@/components/motion/Reveal'
import { useToast } from '@/components/Toast'
import { useAuthStore } from '@/store/authStore'
import type {
  ChatMessage,
  FieldStatus,
  PostDraft,
  PostDraftResponse,
  StandardTag,
} from '@shared/types'

const EMPTY_DRAFT: PostDraft = {
  activity_name: '',
  target_members: 2,
  needed_roles: [],
  weekly_hours: '',
  school_scope: '',
  deadline: '',
  description: '',
}

const FIELD_STATUS_LABEL: Record<FieldStatus, string> = {
  confirmed: '已确认',
  pending: '待补充',
  unknown: '待确认',
  skipped: '已跳过',
  none: '未填写',
}

const initialMessage = (): ChatMessage => ({
  role: 'assistant',
  content:
    '你好！我是你的 AI 组队助手。告诉我你想参加什么活动，或者需要什么样的队友，我来帮你生成组队帖。\n\n例如：「我想参加美赛，还缺两个队友」',
  timestamp: new Date().toISOString(),
})

export default function Publish() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const shouldReduceMotion = useReducedMotion()
  const { user } = useAuthStore()
  const { showToast } = useToast()

  const [messages, setMessages] = useState<ChatMessage[]>([initialMessage()])
  const [input, setInput] = useState('')
  const [draft, setDraft] = useState<PostDraft | null>(null)
  const [draftRevision, setDraftRevision] = useState(0)
  const [isComplete, setIsComplete] = useState(false)
  const [loading, setLoading] = useState(false)
  const [publishing, setPublishing] = useState(false)
  const [editingDraft, setEditingDraft] = useState(false)
  const [useManualForm, setUseManualForm] = useState(false)
  const [fieldStates, setFieldStates] = useState<
    NonNullable<PostDraftResponse['field_states']>
  >({})
  const [candidateTags, setCandidateTags] = useState<StandardTag[]>([])
  const [selectedTagIds, setSelectedTagIds] = useState<string[]>([])

  const kind = searchParams.get('kind') === 'topic_team' ? 'topic_team' : 'casual_invitation'
  const topicId = searchParams.get('topic_id') || undefined
  const scrollRef = useRef<HTMLDivElement>(null)

  const draftIsValid = Boolean(
    draft?.activity_name.trim() &&
      draft.target_members > 0 &&
      draft.needed_roles.length > 0 &&
      draft.weekly_hours.trim() &&
      draft.school_scope.trim() &&
      draft.deadline.trim(),
  )
  const canPublish = draftIsValid && (useManualForm || isComplete)

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: shouldReduceMotion ? 'auto' : 'smooth',
    })
  }, [messages, loading, shouldReduceMotion])

  const activateManualForm = () => {
    setUseManualForm(true)
    setEditingDraft(true)
    setDraft((current) => current || { ...EMPTY_DRAFT })
    setDraftRevision((current) => current + 1)
  }

  const handleSend = async () => {
    if (!input.trim() || loading) return

    const userMsg: ChatMessage = {
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const res = await postDraft({
        message: userMsg.content,
        draft: draft || undefined,
        user_skills: user?.skills,
        kind,
        topic_id: topicId,
        field_states: fieldStates,
      })
      setDraft(res.draft)
      setDraftRevision((current) => current + 1)
      setIsComplete(res.is_complete)
      setFieldStates(res.field_states || {})
      setCandidateTags(res.candidate_tags || [])
      setSelectedTagIds((current) =>
        Array.from(new Set([...current, ...(res.suggested_tag_ids || [])])),
      )
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: res.reply,
          draft: res.draft,
          timestamp: new Date().toISOString(),
        },
      ])
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: '抱歉，AI 服务暂时不可用。你可以切换到手动填写模式直接发布。',
          timestamp: new Date().toISOString(),
        },
      ])
      activateManualForm()
      showToast('AI 服务异常，已切换到手动填写', 'error')
    } finally {
      setLoading(false)
    }
  }

  const handlePublish = async () => {
    if (!draft) return
    if (!draftIsValid) {
      showToast('请完善活动名称、人数、角色、投入、范围和截止日期', 'error')
      return
    }
    setPublishing(true)
    try {
      const post = await createPost({
        title: `${draft.activity_name}队伍招募${draft.needed_roles.join('和')}队友`,
        activity_name: draft.activity_name,
        target_members: draft.target_members,
        needed_roles: draft.needed_roles,
        weekly_hours: draft.weekly_hours,
        school_scope: draft.school_scope,
        deadline: draft.deadline,
        description: draft.description,
        kind,
        topic_id: topicId,
        tag_ids: selectedTagIds,
      })
      showToast('发布成功，正在审核中', 'success')
      navigate(`/posts/${post.id}`)
    } catch {
      showToast('发布失败，请稍后重试', 'error')
    } finally {
      setPublishing(false)
    }
  }

  const handleReset = () => {
    setMessages([
      {
        role: 'assistant',
        content: '好的，让我们重新开始。告诉我你想参加什么活动？',
        timestamp: new Date().toISOString(),
      },
    ])
    setDraft(null)
    setDraftRevision((current) => current + 1)
    setIsComplete(false)
    setUseManualForm(false)
    setEditingDraft(false)
    setFieldStates({})
    setCandidateTags([])
    setSelectedTagIds([])
  }

  const updateDraftField = (field: keyof PostDraft, value: string | number | string[]) => {
    setDraft((prev) => (prev ? { ...prev, [field]: value } : null))
  }

  return (
    <div className="min-h-[calc(100dvh-8rem)] py-2 md:py-4">
      <Reveal as="header" className="mb-5 border-b border-stone pb-5">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div className="min-w-0">
            <p className="section-label mb-2">校园协作编辑部</p>
            <div className="flex items-center gap-2">
              <Sparkles size={19} className="shrink-0 text-primary-600" />
              <h1 className="text-xl font-semibold text-ink sm:text-2xl">AI 对话式发帖</h1>
            </div>
            <p className="mt-2 text-sm text-ink-muted">
              {kind === 'topic_team'
                ? '正在为当前话题发布组队招募'
                : '正在发布同学自主邀约'}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={handleReset} className="btn-secondary">
              <RefreshCw size={15} />
              重新描述
            </button>
            {useManualForm ? (
              <button
                type="button"
                onClick={() => setUseManualForm(false)}
                className="btn-secondary"
              >
                <Sparkles size={15} />
                回到 AI 对话
              </button>
            ) : (
              <button type="button" onClick={activateManualForm} className="btn-secondary">
                <Edit3 size={15} />
                手动填写
              </button>
            )}
          </div>
        </div>
      </Reveal>

      <div className="grid min-w-0 gap-5 lg:grid-cols-[minmax(0,1fr)_22rem] lg:items-start">
        <Reveal
          as="section"
          className="flex min-h-[32rem] min-w-0 flex-col overflow-hidden rounded-card border border-stone bg-paper shadow-panel lg:h-[calc(100dvh-13rem)]"
          delay={0.04}
        >
          <div className="flex items-center justify-between border-b border-stone px-4 py-3">
            <div>
              <h2 className="text-sm font-semibold text-ink">需求对话</h2>
              <p className="mt-0.5 text-xs text-ink-muted">AI 只整理发帖草稿，发布前由你确认</p>
            </div>
            <span className="text-xs font-medium text-campus-green">
              {loading ? '整理中' : useManualForm ? '手动模式' : '可继续对话'}
            </span>
          </div>

          <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto px-3 py-4 sm:px-5">
            <div className="space-y-3">
              <AnimatePresence initial={false}>
                {messages.map((message, index) => (
                  <motion.div
                    key={`${message.timestamp}-${index}`}
                    layout={!shouldReduceMotion}
                    initial={shouldReduceMotion ? false : { opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={shouldReduceMotion ? undefined : { opacity: 0 }}
                    transition={{ duration: shouldReduceMotion ? 0 : 0.18 }}
                    className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[88%] rounded-card border px-3.5 py-3 text-sm leading-6 sm:max-w-[78%] ${
                        message.role === 'user'
                          ? 'border-primary-600 bg-primary-600 text-white'
                          : 'border-stone bg-paper-warm text-ink'
                      }`}
                    >
                      <p className="whitespace-pre-wrap break-words">{message.content}</p>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>

              <AnimatePresence>
                {loading && (
                  <motion.div
                    key="ai-thinking"
                    initial={shouldReduceMotion ? false : { opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={shouldReduceMotion ? undefined : { opacity: 0 }}
                    transition={{ duration: shouldReduceMotion ? 0 : 0.18 }}
                    className="flex justify-start"
                  >
                    <div className="rounded-card border border-stone bg-paper-warm px-4 py-3">
                      <AIThinking />
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>

          <div className="border-t border-stone bg-paper px-3 py-3 sm:px-4">
            <label htmlFor="publish-message" className="mb-1.5 block text-sm font-medium text-ink">
              描述组队需求
            </label>
            <div className="flex min-w-0 gap-2">
              <input
                id="publish-message"
                type="text"
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(event) => event.key === 'Enter' && handleSend()}
                placeholder="例如：我想参加美赛，还缺两位队友"
                disabled={loading}
                autoComplete="off"
                className="input-base min-w-0 flex-1"
              />
              <button
                type="button"
                onClick={handleSend}
                disabled={loading || !input.trim()}
                className="icon-button size-10 bg-primary-600 text-white hover:bg-primary-700 hover:text-white"
                aria-label="发送需求"
                title="发送需求"
              >
                <Send size={17} />
              </button>
            </div>
          </div>
        </Reveal>

        <Reveal
          as="aside"
          className="min-w-0 border-t-2 border-primary-600 bg-paper px-4 py-5 shadow-panel lg:max-h-[calc(100dvh-13rem)] lg:overflow-y-auto"
          delay={0.08}
        >
          <div className="mb-5 flex items-start justify-between gap-3 border-b border-stone pb-4">
            <div>
              <p className="section-label mb-2">结构化稿件</p>
              <h2 className="text-lg font-semibold text-ink">组队帖草稿</h2>
            </div>
            {draft && (
              <button
                type="button"
                onClick={() => setEditingDraft((current) => !current)}
                className="btn-secondary shrink-0 px-3 py-1.5 text-xs"
              >
                <Edit3 size={13} />
                {editingDraft ? '完成编辑' : '编辑草稿'}
              </button>
            )}
          </div>

          <AnimatePresence mode="wait" initial={false}>
            {draft ? (
              <motion.div
                key={`draft-${draftRevision}`}
                initial={shouldReduceMotion ? false : { opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={shouldReduceMotion ? undefined : { opacity: 0, x: -6 }}
                transition={{ duration: shouldReduceMotion ? 0 : 0.18 }}
                className="space-y-4"
              >
                {useManualForm && (
                  <div className="border-l-2 border-campus-gold bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-900">
                    手动模式已开启。请完善必填字段后发布。
                  </div>
                )}

                <DraftField
                  label="活动名称"
                  value={draft.activity_name}
                  status={fieldStates.activity_name?.status}
                  editing={editingDraft}
                  onChange={(value) => updateDraftField('activity_name', value)}
                />
                <DraftField
                  label="目标人数"
                  value={String(draft.target_members)}
                  status={fieldStates.target_members?.status}
                  editing={editingDraft}
                  inputMode="numeric"
                  onChange={(value) => updateDraftField('target_members', Number(value) || 1)}
                />
                <DraftField
                  label="需要角色"
                  value={draft.needed_roles.join('、')}
                  status={fieldStates.needed_roles?.status}
                  editing={editingDraft}
                  onChange={(value) =>
                    updateDraftField(
                      'needed_roles',
                      value.split(/[、,，\s]+/).filter(Boolean),
                    )
                  }
                />
                <DraftField
                  label="每周投入"
                  value={draft.weekly_hours}
                  status={fieldStates.weekly_hours?.status}
                  editing={editingDraft}
                  onChange={(value) => updateDraftField('weekly_hours', value)}
                />
                <DraftField
                  label="组队范围"
                  value={draft.school_scope}
                  status={fieldStates.school_scope?.status}
                  editing={editingDraft}
                  onChange={(value) => updateDraftField('school_scope', value)}
                />
                <DraftField
                  label="截止日期"
                  value={draft.deadline}
                  status={fieldStates.deadline?.status}
                  editing={editingDraft}
                  onChange={(value) => updateDraftField('deadline', value)}
                />
                <DraftField
                  label="补充说明"
                  value={draft.description || ''}
                  status={fieldStates.description?.status}
                  editing={editingDraft}
                  multiline
                  onChange={(value) => updateDraftField('description', value)}
                />

                {candidateTags.length > 0 && (
                  <section className="border-t border-stone pt-4" aria-labelledby="standard-tags-title">
                    <div className="mb-2 flex items-center justify-between gap-3">
                      <h3 id="standard-tags-title" className="text-xs font-semibold text-ink">
                        标准标签
                      </h3>
                      <span className="text-[11px] text-ink-muted">仅可选择标准标签</span>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      <AnimatePresence initial={false}>
                        {candidateTags
                          .filter((tag) => selectedTagIds.includes(tag.tag_id))
                          .map((tag) => (
                            <motion.span
                              layout={!shouldReduceMotion}
                              key={tag.tag_id}
                              initial={shouldReduceMotion ? false : { opacity: 0, scale: 0.96 }}
                              animate={{ opacity: 1, scale: 1 }}
                              exit={shouldReduceMotion ? undefined : { opacity: 0, scale: 0.96 }}
                              transition={{ duration: shouldReduceMotion ? 0 : 0.16 }}
                              className="tag-chip"
                            >
                              <span className="max-w-[12rem] break-words">{tag.canonical_name}</span>
                              <button
                                type="button"
                                onClick={() =>
                                  setSelectedTagIds((items) =>
                                    items.filter((id) => id !== tag.tag_id),
                                  )
                                }
                                className="inline-flex size-5 items-center justify-center rounded-full hover:bg-primary-200"
                                aria-label={`移除${tag.canonical_name}`}
                                title={`移除${tag.canonical_name}`}
                              >
                                <X size={12} />
                              </button>
                            </motion.span>
                          ))}
                      </AnimatePresence>
                    </div>
                    {candidateTags.some((tag) => !selectedTagIds.includes(tag.tag_id)) && (
                      <select
                        className="input-base mt-2 text-xs"
                        value=""
                        onChange={(event) => {
                          if (event.target.value) {
                            setSelectedTagIds((items) => [...items, event.target.value])
                          }
                        }}
                        aria-label="添加标准标签"
                      >
                        <option value="">添加标准标签</option>
                        {candidateTags
                          .filter((tag) => !selectedTagIds.includes(tag.tag_id))
                          .map((tag) => (
                            <option key={tag.tag_id} value={tag.tag_id}>
                              {tag.canonical_name}
                            </option>
                          ))}
                      </select>
                    )}
                  </section>
                )}

                <div className="border-t border-stone pt-4">
                  <button
                    type="button"
                    onClick={handlePublish}
                    disabled={publishing || !canPublish}
                    className="btn-primary min-h-11 w-full"
                  >
                    <Check size={16} />
                    {publishing ? '发布中...' : canPublish ? '确认发布' : '继续完善信息'}
                  </button>
                  {!canPublish && (
                    <p className="mt-2 text-center text-xs leading-5 text-ink-muted">
                      {useManualForm ? '请补全必填字段后发布' : 'AI 正在帮你补全信息，完善后可发布'}
                    </p>
                  )}
                </div>
              </motion.div>
            ) : (
              <motion.div
                key="empty-draft"
                initial={shouldReduceMotion ? false : { opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={shouldReduceMotion ? undefined : { opacity: 0 }}
                transition={{ duration: shouldReduceMotion ? 0 : 0.18 }}
                className="py-12 text-center text-sm text-ink-muted"
              >
                <Sparkles size={28} className="mx-auto mb-3 text-primary-300" />
                <p>开始对话后，AI 会在这里生成草稿</p>
              </motion.div>
            )}
          </AnimatePresence>
        </Reveal>
      </div>
    </div>
  )
}

function DraftField({
  label,
  value,
  status,
  editing,
  multiline = false,
  inputMode,
  onChange,
}: {
  label: string
  value: string
  status?: FieldStatus
  editing: boolean
  multiline?: boolean
  inputMode?: 'numeric'
  onChange: (value: string) => void
}) {
  const fieldId = `draft-${label}`

  return (
    <div className="min-w-0">
      <div className="mb-1 flex items-center justify-between gap-3">
        <label htmlFor={fieldId} className="text-xs font-semibold text-ink-muted">
          {label}
        </label>
        {status && (
          <span
            className={`shrink-0 text-[11px] font-medium ${
              status === 'confirmed' ? 'text-campus-green' : 'text-campus-gold'
            }`}
          >
            {FIELD_STATUS_LABEL[status]}
          </span>
        )}
      </div>
      {editing ? (
        multiline ? (
          <textarea
            id={fieldId}
            value={value}
            onChange={(event) => onChange(event.target.value)}
            rows={3}
            className="input-base resize-y text-sm leading-6"
          />
        ) : (
          <input
            id={fieldId}
            type="text"
            inputMode={inputMode}
            value={value}
            onChange={(event) => onChange(event.target.value)}
            className="input-base text-sm"
          />
        )
      ) : (
        <p className="break-words border-b border-stone pb-2 text-sm leading-6 text-ink">
          {value || '暂无'}
        </p>
      )}
    </div>
  )
}
