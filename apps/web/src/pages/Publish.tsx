import { useCallback, useEffect, useRef, useState } from 'react'
import { CalendarPlus, Check, RotateCcw, Send } from 'lucide-react'
import { Link, useSearchParams } from 'react-router-dom'
import { postDraft } from '@/api/agent'
import { createPost } from '@/api/posts'
import { getPublishContext, uploadPostCover } from '@/api/publish'
import CampusGrowth, { PlantBorder } from '@/components/publish/CampusGrowth'
import WhaleWaiting, { Whale } from '@/components/publish/WhaleWaiting'
import { PublishReview } from '@/components/publish/PublishReview'
import { completeness, emptyDraft, missingFields, normalizeDraft, purposeLabels, requestError } from '@/features/publish/publishState'
import type { FieldStates, PublishContext, PublishPhase } from '@/features/publish/publishState'
import { useAuthStore } from '@/store/authStore'
import type { ChatMessage, PostDraft, PostDraftRequest, PostPurpose, StandardTag, WorkflowFieldStates, WorkflowPostDraft } from '@shared/types'

export default function Publish() {
  const [params] = useSearchParams()
  const user = useAuthStore((state) => state.user)
  const kind = params.get('kind') === 'topic_team' ? 'topic_team' : 'casual_invitation'
  const topicId = params.get('topic_id') || undefined
  const canPublishActivity = Boolean(user?.identity?.is_staff || user?.identity?.platform_role || user?.identity?.organization_roles.some(({ role }) => role === 'owner' || role === 'publisher'))
  return <PublishSession key={`${user?.id}:${kind}:${topicId}`} userId={user?.id || ''} kind={kind} topicId={topicId} canPublishActivity={canPublishActivity} />
}

function PublishSession({ userId, kind, topicId, canPublishActivity }: { userId: string; kind: PublishContext['kind']; topicId?: string; canPublishActivity: boolean }) {
  const [context, setContext] = useState<PublishContext | null>(null)
  const [contextError, setContextError] = useState('')
  const [contextLoading, setContextLoading] = useState(true)
  const [purpose, setPurpose] = useState<PostPurpose>('team_recruitment')
  const [phase, setPhase] = useState<PublishPhase>('conversation')
  const [draft, setDraft] = useState<PostDraft>({ ...emptyDraft })
  const [states, setStates] = useState<FieldStates>({})
  const [workflowDraft, setWorkflowDraft] = useState<WorkflowPostDraft>({})
  const [workflowStates, setWorkflowStates] = useState<WorkflowFieldStates>({})
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [error, setError] = useState('')
  const [degraded, setDegraded] = useState(false)
  const [candidates, setCandidates] = useState<StandardTag[]>([])
  const [tags, setTags] = useState<string[]>([])
  const [cover, setCover] = useState<{ file: File; preview: string; id?: string } | null>(null)
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState<string | null>(null)
  const [publishingSeconds, setPublishingSeconds] = useState(0)
  const [restorable, setRestorable] = useState(false)
  const requestId = useRef<string>(crypto.randomUUID())
  const busy = useRef(false)
  const generation = useRef(0)
  const contextSequence = useRef(0)
  const uploadSequence = useRef(0)
  const retryMessage = useRef('')
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const historyRef = useRef<HTMLDivElement>(null)
  const reviewRef = useRef<HTMLHeadingElement>(null)
  const storageKey = `campusmate.publish.v2:${userId}:${kind}:${topicId || ''}`

  const loadContext = useCallback(async () => {
    const sequence = ++contextSequence.current
    setContextLoading(true); setContextError('')
    try {
      const value = await getPublishContext(kind, topicId)
      if (sequence !== contextSequence.current) return
      setContext(value)
      setPurpose((old) => value.allowed_purposes.includes(old) ? old : value.default_purpose)
      setDraft((old) => ({ ...old, ...value.defaults }))
      setStates((old) => ({ ...old, ...Object.fromEntries(Object.entries(value.defaults).filter(([, v]) => Boolean(v)).map(([k, v]) => [k, { value: v, status: 'confirmed' }])) }))
      try { setRestorable(Boolean(sessionStorage.getItem(storageKey))) } catch { /* Optional storage. */ }
    } catch (err) {
      if (sequence === contextSequence.current) setContextError(requestError(err, '暂时无法加载发布权限，请重试。'))
    } finally { if (sequence === contextSequence.current) setContextLoading(false) }
  }, [kind, topicId, storageKey])

  useEffect(() => {
    void loadContext()
    return () => { generation.current++; contextSequence.current++; uploadSequence.current++ }
  }, [loadContext])
  useEffect(() => { if (historyRef.current) historyRef.current.scrollTop = historyRef.current.scrollHeight }, [messages])
  useEffect(() => { if (phase === 'review') reviewRef.current?.focus() }, [phase])
  const coverPreview = cover?.preview
  useEffect(() => () => { if (coverPreview) URL.revokeObjectURL(coverPreview) }, [coverPreview])
  useEffect(() => {
    if (!context || restorable || phase === 'published' || (!messages.length && !draft.activity_name && !input)) return
    try { sessionStorage.setItem(storageKey, JSON.stringify({ draft, states, workflowDraft, workflowStates, messages: messages.slice(-30), input, purpose, tags, requestId: requestId.current, revision: context.revision, savedAt: Date.now() })) } catch { /* Optional storage. */ }
  }, [context, restorable, phase, draft, states, workflowDraft, workflowStates, messages, input, purpose, tags, storageKey])
  useEffect(() => useAuthStore.subscribe((next) => {
    if (!next.isAuthenticated) { try { sessionStorage.removeItem(storageKey) } catch { /* Optional storage. */ } }
  }), [storageKey])
  useEffect(() => {
    if (phase !== 'publishing') {
      setPublishingSeconds(0)
      return
    }
    const startedAt = Date.now()
    const timer = window.setInterval(() => {
      setPublishingSeconds(Math.floor((Date.now() - startedAt) / 1000))
    }, 1000)
    return () => window.clearInterval(timer)
  }, [phase])
  useEffect(() => {
    if (phase !== 'publishing') return
    const protectSubmission = (event: BeforeUnloadEvent) => {
      event.preventDefault()
      event.returnValue = ''
    }
    window.addEventListener('beforeunload', protectSubmission)
    return () => window.removeEventListener('beforeunload', protectSubmission)
  }, [phase])

  const updateField = (field: keyof PostDraft, value: string | number | string[]) => {
    setDraft((old) => ({ ...old, [field]: value }))
    const isEmpty = Array.isArray(value) ? !value.length : !value
    setStates((old) => ({ ...old, [field]: { value, status: isEmpty ? (field === 'needed_roles' ? 'none' : 'pending') : 'confirmed' } }))
  }
  const send = async (retry = false) => {
    const text = retry ? retryMessage.current : input.trim()
    if (!context || !text || busy.current || uploading || restorable) return
    busy.current = true
    const sequence = ++generation.current
    retryMessage.current = text
    setError(''); setPhase('thinking')
    if (!retry) setMessages((old) => [...old, { role: 'user', content: text, timestamp: new Date().toISOString() }])
    setInput('')
    try {
      const response = await postDraft({
        message: text, draft, workflow_draft: workflowDraft, workflow_field_states: workflowStates, kind, topic_id: topicId, purpose, publish_context_revision: context.revision,
        field_states: Object.fromEntries(Object.entries(states).map(([key, state]) => [key, { ...state, value: Array.isArray(state.value) ? state.value.join('、') : state.value }])) as PostDraftRequest['field_states'],
      })
      if (sequence !== generation.current) return
      if (response.blocked) { setError(response.reply || '请调整描述后再试。'); setPhase('conversation'); return }
      const nextDraft = normalizeDraft(response.draft || draft)
      if (context.activity) nextDraft.activity_name = context.activity.title
      const nextStates = response.field_states || {}
      setDraft(nextDraft); setStates(nextStates); setCandidates(response.candidate_tags || [])
      if (!response.degraded) {
        setWorkflowDraft(response.workflow_draft || workflowDraft)
        setWorkflowStates(response.workflow_field_states || workflowStates)
      }
      setTags((old) => [...new Set([...old, ...(response.suggested_tag_ids || [])])].filter((id) => !context.inherited_tags.some((tag) => tag.tag_id === id)).slice(0, Math.max(0, 8 - context.inherited_tags.length)))
      setMessages((old) => [...old, { role: 'assistant', content: response.reply, timestamp: new Date().toISOString() }])
      const responseDegraded = Boolean(response.degraded)
      setDegraded(responseDegraded)
      const workflowComplete = Boolean(response.workflow_draft) && response.is_complete
      const legacyComplete = !response.workflow_draft && response.is_complete && missingFields(nextDraft, nextStates, context, purpose).length === 0
      setPhase(workflowComplete || legacyComplete ? 'review' : 'conversation')
      if (!responseDegraded) retryMessage.current = ''
    } catch (err) {
      if (sequence !== generation.current) return
      setError(requestError(err, '暂时没有收到回复，你的内容已保留。请重试或手动完善。')); setPhase('conversation')
    } finally { if (sequence === generation.current) { busy.current = false; inputRef.current?.focus() } }
  }
  const publish = async () => {
    if (!context || busy.current || uploading) return
    const missing = missingFields(draft, states, context, purpose)
    if (missing.length) { setError('请先补全标出的必填内容。'); document.getElementById(`publish-${missing[0]}`)?.focus(); return }
    if (cover && !cover.id) { setError('封面还未上传成功，请重试或移除封面。'); return }
    busy.current = true
    const sequence = ++generation.current
    setError(''); setPhase('publishing')
    try {
      const post = await createPost({ ...draft, ...(purpose === 'discussion' ? { target_members: 1, needed_roles: [], weekly_hours: '', school_scope: '', deadline: '' } : {}), title: draft.activity_name, kind, topic_id: topicId, purpose, tag_ids: tags, client_request_id: requestId.current, cover_upload_id: cover?.id, publish_context_revision: context.revision })
      if (sequence !== generation.current) return
      setResult(post.id); setPhase('published')
      try { sessionStorage.removeItem(storageKey) } catch { /* Optional storage. */ }
    } catch (err) {
      if (sequence === generation.current) { setError(requestError(err, '未能确认发布结果，内容已保留。重试不会重复发布。')); setPhase('review') }
    } finally { if (sequence === generation.current) busy.current = false }
  }
  const upload = async (file: File) => {
    const sequence = ++uploadSequence.current
    const preview = URL.createObjectURL(file)
    setCover({ file, preview }); setUploading(true); setError('')
    try {
      const id = await uploadPostCover(file)
      if (sequence === uploadSequence.current) setCover({ file, preview, id })
    } catch (err) {
      if (sequence === uploadSequence.current) setError(requestError(err, '封面上传失败，请重试。'))
    } finally { if (sequence === uploadSequence.current) setUploading(false) }
  }
  const restore = () => {
    try {
      const saved = JSON.parse(sessionStorage.getItem(storageKey) || '{}')
      if (!context || !Number.isFinite(saved.savedAt) || Date.now() - saved.savedAt > 86400000 || saved.revision !== context.revision || !context.allowed_purposes.includes(saved.purpose)) throw new Error('stale')
      setDraft({ ...normalizeDraft(saved.draft || {}), ...(context.activity ? { activity_name: context.activity.title } : {}) })
      setStates(saved.states || {}); setPurpose(saved.purpose)
      setWorkflowDraft(saved.workflowDraft || {}); setWorkflowStates(saved.workflowStates || {})
      setMessages(Array.isArray(saved.messages) ? saved.messages.filter((m: ChatMessage) => ['user', 'assistant'].includes(m.role) && typeof m.content === 'string') : [])
      setInput(typeof saved.input === 'string' ? saved.input : '')
      setTags(Array.isArray(saved.tags) ? saved.tags.filter((tag: unknown) => typeof tag === 'string').slice(0, 8) : [])
      if (/^[a-zA-Z0-9-]{16,64}$/.test(saved.requestId)) requestId.current = saved.requestId
      setError('')
    } catch { setError('旧草稿已过期或活动规则已变化，请重新确认资料。') }
    setRestorable(false)
  }
  const reset = () => {
    if (!window.confirm('清空本次对话和草稿，重新开始？')) return
    generation.current++; uploadSequence.current++; busy.current = false
    setDraft({ ...emptyDraft, ...context?.defaults }); setStates({}); setWorkflowDraft({}); setWorkflowStates({})
    setMessages([]); setInput(''); setError(''); setTags([]); setCover(null); setUploading(false)
    setRestorable(false); setDegraded(false); setPhase('conversation'); setResult(null)
    requestId.current = crypto.randomUUID(); retryMessage.current = ''
    try { sessionStorage.removeItem(storageKey) } catch { /* Optional storage. */ }
  }

  if (contextLoading) return <div className="publish-experience py-12" role="status">正在准备发布空间…</div>
  if (!context || contextError) return <div className="publish-experience py-12"><p role="alert">{contextError}</p><button className="btn btn-secondary mt-4" onClick={() => void loadContext()}>重新加载</button></div>
  const progress = completeness(draft, states, context, purpose)
  const locked = phase === 'thinking' || phase === 'publishing'
  const reviewing = phase === 'review' || phase === 'publishing'
  return <div className="publish-experience py-6 sm:py-10">
    <header className="flex items-center justify-between gap-4 mb-5 px-1">
      <div><p className="text-sm text-gray-500 mb-1">和小蓝鲸一起</p><h1 className="text-2xl sm:text-3xl font-bold">让想法找到伙伴</h1></div>
      <div className="flex items-center gap-2">{canPublishActivity && <Link aria-disabled={locked} onClick={(event) => { if (locked) event.preventDefault() }} className={`btn-secondary ${locked ? 'pointer-events-none opacity-50' : ''}`} to="/publish/activity"><CalendarPlus size={17} />正式活动</Link>}<button className="publish-icon" title="重新开始" aria-label="重新开始" disabled={locked} onClick={reset}><RotateCcw size={20} /></button></div>
    </header>
    {context.activity && <div className="publish-context mb-4"><span>关联活动</span><Link to={`/topics/${context.activity.id}`} className="font-semibold">{context.activity.title}</Link></div>}
    {context.allowed_purposes.length > 1 && <div className="flex flex-wrap gap-2 mb-5" role="group" aria-label="发布用途">{context.allowed_purposes.map((item) => <button key={item} className={`publish-purpose ${purpose === item ? 'is-active' : ''}`} aria-pressed={purpose === item} disabled={locked || phase === 'published' || restorable} onClick={() => { setPurpose(item); setPhase('conversation'); setError(''); retryMessage.current = '' }}>{purposeLabels[item]}</button>)}</div>}
    {restorable && <div className="publish-restore mb-4"><span>有一份尚未发布的草稿</span><button onClick={restore}>继续填写</button><button onClick={() => { try { sessionStorage.removeItem(storageKey) } catch { /* Optional storage. */ } setRestorable(false) }}>放弃</button></div>}
    <div className="publish-dialog" aria-busy={locked}>
      <div className="publish-dialog-content">
        {phase === 'published' ? <div className="text-center py-16 px-6"><Check size={42} className="mx-auto mb-4 text-emerald-600" /><h2 className="text-2xl font-bold mb-3">发布成功，等伙伴来相遇</h2><div className="flex gap-3 justify-center flex-wrap"><Link className="btn btn-primary" to={`/posts/${result}`}>查看帖子</Link><Link className="btn btn-secondary" to="/my/groups">我的组队</Link></div></div> : reviewing ?
          <PublishReview headingRef={reviewRef} draft={draft} states={states} context={context} purpose={purpose} updateField={updateField} tags={tags} setTags={setTags} candidates={candidates} cover={cover} upload={upload} removeCover={() => { uploadSequence.current++; setCover(null); setUploading(false) }} uploading={uploading} locked={locked} publishingSeconds={publishingSeconds} publish={() => void publish()} back={() => { setPhase('conversation'); setError('') }} /> : <>
            <div className="publish-messages" ref={historyRef} role="log" aria-label="发布对话" aria-live="polite">
              <div className="flex items-center gap-2 mb-3"><div style={{ width: 42 }}><Whale /></div><span className="font-semibold text-sm">小蓝鲸</span></div>
              <div className="publish-bubble publish-bubble-assistant mb-4">{purpose === 'discussion' ? '想请教经验，还是分享一个新发现？和我说说吧。' : purpose === 'official_signup' ? '介绍一下这场活动，我来帮你整理报名信息。' : '你想做什么，想遇见怎样的伙伴？先从一句话开始吧。'}</div>
              {messages.map((message, index) => <div key={index} className={`publish-bubble publish-bubble-${message.role} mb-4`}>{message.content}</div>)}
            </div>
            <form className="publish-composer" onSubmit={(event) => { event.preventDefault(); void send() }}>
              <textarea ref={inputRef} aria-label="描述你的想法" placeholder="比如：这周末想找几位同学一起打羽毛球…" value={input} maxLength={4000} disabled={locked || restorable} rows={2} onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); void send() } }} />
              <button type="submit" className="publish-send" title="发送" aria-label="发送" disabled={!input.trim() || locked || restorable}><Send size={20} /></button>
            </form>
          </>}
        {phase === 'thinking' && <WhaleWaiting />}
      </div>
      {error && <div className="publish-feedback" role="alert"><p>{error}</p><div className="flex gap-4 mt-2">{retryMessage.current && phase === 'conversation' && <button onClick={() => void send(true)}>重试回复</button>}{error.includes('规则') && <button onClick={() => { setRestorable(false); void loadContext() }}>刷新活动规则</button>}</div></div>}
      {degraded && phase === 'conversation' && <p className="px-6 pt-3 text-sm text-gray-500">AI 服务暂时未响应，当前内容已经保留。<button className="ml-2 font-semibold text-purple-700 hover:text-purple-900" onClick={() => void send(true)}>重试 AI</button></p>}
      <PlantBorder progress={progress} />
    </div>
    <div className="text-center mt-3 min-h-6">{phase === 'conversation' && <button className="text-sm text-gray-500 hover:text-gray-900" disabled={restorable} onClick={() => setPhase('review')}>手动完善资料</button>}</div>
    <CampusGrowth progress={progress} published={phase === 'published'} />
  </div>
}
