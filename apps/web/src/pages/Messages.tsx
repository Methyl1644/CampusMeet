import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { motion, useReducedMotion } from 'motion/react'
import { ArrowLeft, Handshake, Lock, Send, XCircle } from 'lucide-react'
import { closeConversation, confirmTeam, getConversation, getConversations, getMessages, sendMessage } from '@/api/messages'
import type { Conversation, Message } from '@shared/types'
import Loading from '@/components/Loading'
import EmptyState from '@/components/EmptyState'
import { useToast } from '@/components/Toast'
import { Link, useNavigate, useParams } from 'react-router-dom'

const messagePageSize = 30

function mergeMessages(current: Message[], incoming: Message[]) {
  const byId = new Map(current.map((message) => [message.id, message]))
  for (const message of incoming) byId.set(message.id, message)
  return [...byId.values()].sort((left, right) => Number(left.id) - Number(right.id))
}

export default function Messages() {
  const { conversationId } = useParams()
  const navigate = useNavigate()
  const { showToast } = useToast()
  const shouldReduceMotion = useReducedMotion()

  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeConv, setActiveConv] = useState<Conversation | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [mobileChatOpen, setMobileChatOpen] = useState(false)
  const [hasOlder, setHasOlder] = useState(false)
  const [loadingOlder, setLoadingOlder] = useState(false)
  const [teamId, setTeamId] = useState<string | null>(null)

  const scrollRef = useRef<HTMLDivElement>(null)
  const messagesRef = useRef<Message[]>([])
  const stickToBottomRef = useRef(true)
  const historyScrollRef = useRef<{ height: number; top: number } | null>(null)
  const activeConversationId = activeConv?.id

  useEffect(() => {
    const fetchConversations = async () => {
      setLoading(true)
      try {
        const data = await getConversations()
        setConversations(data)
        if (conversationId) {
          const selected = data.find((item) => item.id === conversationId)
          if (selected) {
            setActiveConv(selected)
            setMobileChatOpen(true)
          }
        }
      } catch {
        showToast('加载会话失败', 'error')
      } finally {
        setLoading(false)
      }
    }
    fetchConversations()
  }, [conversationId]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!activeConversationId) return
    let cancelled = false
    const currentConversationId = activeConversationId
    const fetchMessages = async () => {
      try {
        const page = await getMessages(currentConversationId, { latest: true, page_size: messagePageSize })
        if (cancelled) return
        messagesRef.current = page.list
        setMessages(page.list)
        setHasOlder(page.total > page.list.length)
      } catch {
        if (!cancelled) showToast('加载消息失败', 'error')
      }
    }
    messagesRef.current = []
    stickToBottomRef.current = true
    historyScrollRef.current = null
    setMessages([])
    setTeamId(activeConv?.team_id ?? null)
    void fetchMessages()

    const interval = window.setInterval(async () => {
      if (document.visibilityState === 'hidden') return
      const lastMessage = messagesRef.current[messagesRef.current.length - 1]
      try {
        const page = await getMessages(currentConversationId, lastMessage ? {
            after_id: lastMessage.id,
            page_size: messagePageSize,
          } : { latest: true, page_size: messagePageSize })
        if (!cancelled && page.list.length > 0) {
          const merged = mergeMessages(messagesRef.current, page.list)
          messagesRef.current = merged
          setMessages(merged)
        }
        const refreshedActive = await getConversation(currentConversationId)
        if (cancelled) return
        setConversations((current) => current.map((item) => (
          item.id === currentConversationId ? refreshedActive : item
        )))
        setActiveConv(refreshedActive)
        setTeamId(refreshedActive.team_id ?? null)
      } catch {
        // The next interval retries; avoid repeated interruption to the conversation.
      }
    }, 5000)

    return () => {
      cancelled = true
      window.clearInterval(interval)
    }
  }, [activeConversationId]) // eslint-disable-line react-hooks/exhaustive-deps

  useLayoutEffect(() => {
    const container = scrollRef.current
    if (!container) return
    const historyScroll = historyScrollRef.current
    if (historyScroll) {
      container.scrollTop = historyScroll.top + container.scrollHeight - historyScroll.height
      historyScrollRef.current = null
      return
    }
    if (stickToBottomRef.current) {
      container.scrollTo?.({
        top: container.scrollHeight,
        behavior: shouldReduceMotion ? 'auto' : 'smooth',
      })
    }
  }, [messages, shouldReduceMotion])

  const handleSend = async () => {
    if (!input.trim() || !activeConv || sending) return
    setSending(true)
    const content = input.trim()
    setInput('')
    try {
      const msg = await sendMessage(activeConv.id, content)
      const merged = mergeMessages(messagesRef.current, [msg])
      messagesRef.current = merged
      setMessages(merged)
    } catch {
      showToast('发送失败', 'error')
      setInput(content)
    } finally {
      setSending(false)
    }
  }

  const handleConfirmTeam = async () => {
    if (!activeConv) return
    try {
      const result = await confirmTeam(activeConv.id)
      if (result.contact_unlocked && result.team_id) {
        setTeamId(result.team_id)
        setActiveConv((prev) => prev ? {
          ...prev, status: 'team_confirmed', contact_unlocked: true,
          my_confirmed: true, team_id: result.team_id,
        } : null)
        showToast('双方已确认，团队空间已创建', 'success')
      } else {
        setActiveConv((prev) => prev ? { ...prev, my_confirmed: true } : null)
        showToast('已确认，等待对方确认', 'success')
      }
      setConversations((current) => current.map((conversation) => (
        conversation.id === activeConv.id
          ? {
              ...conversation,
              status: result.contact_unlocked ? 'team_confirmed' : conversation.status,
              contact_unlocked: Boolean(result.contact_unlocked),
              my_confirmed: true,
              team_id: result.team_id ?? conversation.team_id,
            }
          : conversation
      )))
    } catch {
      showToast('操作失败', 'error')
    }
  }

  const handleClose = async () => {
    if (!activeConv) return
    try {
      await closeConversation(activeConv.id)
      showToast('对话已结束', 'info')
      setActiveConv(null)
      setMobileChatOpen(false)
      navigate('/messages', { replace: true })
      const data = await getConversations()
      setConversations(data)
    } catch {
      showToast('操作失败', 'error')
    }
  }

  const openConversation = (conv: Conversation) => {
    setActiveConv(conv)
    setMobileChatOpen(true)
    navigate(`/messages/${conv.id}`)
  }

  const loadOlderMessages = async () => {
    if (!activeConv || loadingOlder || messages.length === 0) return
    const container = scrollRef.current
    if (container) {
      historyScrollRef.current = { height: container.scrollHeight, top: container.scrollTop }
      stickToBottomRef.current = false
    }
    setLoadingOlder(true)
    try {
      const page = await getMessages(activeConv.id, {
        before_id: messages[0].id,
        page_size: messagePageSize,
      })
      const merged = mergeMessages(page.list, messagesRef.current)
      messagesRef.current = merged
      setMessages(merged)
      setHasOlder(merged.length < page.total && page.list.length > 0)
    } catch {
      showToast('加载历史消息失败', 'error')
    } finally {
      setLoadingOlder(false)
    }
  }

  if (loading) return <Loading />

  return (
    <div className="-mx-4 -mt-6 grid h-[calc(100dvh-5rem-env(safe-area-inset-bottom))] min-h-[28rem] grid-cols-1 overflow-hidden border-y border-stone bg-paper sm:-mx-6 md:mx-0 md:mt-0 md:h-[calc(100dvh-10rem)] md:min-h-[32rem] md:grid-cols-[20rem_minmax(0,1fr)] md:rounded-card md:border">
      <aside className={`${mobileChatOpen ? 'hidden' : 'flex'} min-w-0 flex-col overflow-hidden border-stone md:flex md:border-r`} aria-label="会话列表">
        <header className="shrink-0 border-b border-stone px-4 py-4">
          <p className="section-label">沟通中心</p>
          <h1 className="mt-2 font-serif text-xl font-semibold text-ink">消息</h1>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto">
          {conversations.length === 0 ? (
            <EmptyState title="暂无会话" />
          ) : (
            conversations.map((conv) => (
              <button
                key={conv.id}
                onClick={() => openConversation(conv)}
                aria-current={activeConv?.id === conv.id ? 'true' : undefined}
                className={`flex min-h-20 w-full items-start gap-3 border-b border-stone px-4 py-3 text-left transition-colors ${
                  activeConv?.id === conv.id
                    ? 'border-l-2 border-l-primary-600 bg-primary-50'
                    : 'border-l-2 border-l-transparent hover:bg-paper-warm'
                }`}
              >
                <div className="flex size-10 shrink-0 items-center justify-center rounded-full bg-primary-100 text-sm font-semibold text-primary-700">
                  {conv.other_user.nickname.charAt(0)}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="truncate text-sm font-semibold text-ink">
                      {conv.other_user.nickname}
                    </span>
                    <span className="shrink-0 text-[11px] tabular-nums text-ink-muted">
                      {conv.last_message_at || '暂无'}
                    </span>
                  </div>
                  <p className="mt-1 truncate text-xs text-ink-muted">{conv.last_message || '暂无'}</p>
                  {conv.unread_count > 0 && (
                    <span className="mt-1 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-red-600 px-1 text-[11px] font-semibold tabular-nums text-white">
                      {conv.unread_count}
                    </span>
                  )}
                </div>
              </button>
            ))
          )}
        </div>
      </aside>

      <section className={`${mobileChatOpen ? 'flex' : 'hidden'} min-w-0 flex-col overflow-hidden bg-paper md:flex`} aria-label="当前对话">
        {activeConv ? (
          <>
            <header className="shrink-0 border-b border-stone px-3 py-3 sm:px-4">
              <div className="flex min-w-0 items-start gap-2">
                <button
                  type="button"
                  onClick={() => { setMobileChatOpen(false); navigate('/messages') }}
                  className="icon-button -ml-2 -mt-1 md:hidden"
                  aria-label="返回会话列表"
                  title="返回会话列表"
                >
                  <ArrowLeft aria-hidden="true" size={18} />
                </button>
                <div className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-semibold text-ink">
                    {activeConv.other_user.nickname}
                  </span>
                  <p className="mt-0.5 truncate text-xs text-ink-muted">{activeConv.post_title}</p>
                </div>
                <div className="flex shrink-0 gap-1.5">
                  {activeConv.status === 'active' && !activeConv.my_confirmed && (
                    <button onClick={handleConfirmTeam} className="btn-secondary min-h-9 px-2.5 text-xs sm:px-3">
                      <Handshake aria-hidden="true" size={14} />
                      <span className="hidden sm:inline">愿意组队</span>
                      <span className="sm:hidden">确认</span>
                    </button>
                  )}
                  <button onClick={handleClose} className="btn-secondary min-h-9 px-2.5 text-xs text-red-700 sm:px-3">
                    <XCircle aria-hidden="true" size={14} />
                    结束
                  </button>
                </div>
              </div>
            </header>

            <div
              ref={scrollRef}
              className="min-h-0 flex-1 overflow-y-auto bg-paper-warm/45 px-3 py-4 sm:px-5"
              onScroll={(event) => {
                const target = event.currentTarget
                stickToBottomRef.current = target.scrollHeight - target.scrollTop - target.clientHeight < 80
              }}
            >
              <div className="space-y-3" aria-live="polite">
                {hasOlder && (
                  <div className="flex justify-center">
                    <button type="button" className="btn-secondary min-h-8 px-3 text-xs" disabled={loadingOlder} onClick={() => void loadOlderMessages()}>
                      {loadingOlder ? '加载中...' : '查看更早消息'}
                    </button>
                  </div>
                )}
                {messages.map((msg) => (
                  <motion.div
                    key={msg.id}
                    initial={shouldReduceMotion ? false : { opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={shouldReduceMotion ? { duration: 0 } : { duration: 0.18 }}
                    className={`flex ${msg.is_mine ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[82%] break-words rounded-card border px-3.5 py-2.5 text-sm leading-6 sm:max-w-[72%] ${
                        msg.is_mine
                          ? 'border-primary-600 bg-primary-600 text-white'
                          : 'border-stone bg-paper text-ink'
                      }`}
                    >
                      {msg.content}
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>

            {activeConv.status === 'closed' ? (
              <div className="shrink-0 border-t border-stone p-3 text-center text-sm text-ink-muted">
                对话已结束
              </div>
            ) : (
              <div className="shrink-0 border-t border-stone bg-paper p-3">
                {activeConv.status === 'team_confirmed' && teamId ? (
                  <div className="mb-3 flex min-h-10 items-center justify-between gap-3 bg-green-50 px-3 text-sm font-medium text-campus-green">
                    <span className="inline-flex items-center gap-2"><Lock aria-hidden="true" size={14} />双方已确认组队</span>
                    <Link to={`/teams/${teamId}`} className="font-semibold underline underline-offset-4">进入团队空间</Link>
                  </div>
                ) : activeConv.my_confirmed ? (
                  <div className="mb-3 flex min-h-10 items-center justify-center gap-2 bg-primary-50 px-3 text-sm font-medium text-primary-700">
                    <Handshake aria-hidden="true" size={14} />已确认，等待对方确认
                  </div>
                ) : null}
                <div className="flex min-w-0 gap-2">
                  <label htmlFor="message-input" className="sr-only">输入消息</label>
                  <input
                    id="message-input"
                    type="text"
                    value={input}
                    onChange={(event) => setInput(event.target.value)}
                    onKeyDown={(event) => event.key === 'Enter' && handleSend()}
                    disabled={sending}
                    className="input-base min-w-0 flex-1"
                  />
                  <button
                    onClick={handleSend}
                    disabled={sending || !input.trim()}
                    className="btn-primary size-10 shrink-0 p-0"
                    aria-label="发送消息"
                    title="发送消息"
                  >
                    <Send aria-hidden="true" size={17} />
                  </button>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="flex min-h-0 flex-1 items-center justify-center">
            <EmptyState title="未选择会话" />
          </div>
        )}
      </section>
    </div>
  )
}
