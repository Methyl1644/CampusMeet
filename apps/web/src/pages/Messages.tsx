import { useEffect, useRef, useState } from 'react'
import { motion, useReducedMotion } from 'motion/react'
import { ArrowLeft, Handshake, Lock, Send, XCircle } from 'lucide-react'
import { closeConversation, confirmTeam, getConversations, getMessages, sendMessage } from '@/api/messages'
import type { Conversation, Message } from '@shared/types'
import Loading from '@/components/Loading'
import EmptyState from '@/components/EmptyState'
import { useToast } from '@/components/Toast'

export default function Messages() {
  const { showToast } = useToast()
  const shouldReduceMotion = useReducedMotion()

  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeConv, setActiveConv] = useState<Conversation | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [mobileChatOpen, setMobileChatOpen] = useState(false)

  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const fetchConversations = async () => {
      setLoading(true)
      try {
        const data = await getConversations()
        setConversations(data)
      } catch {
        showToast('加载会话失败', 'error')
      } finally {
        setLoading(false)
      }
    }
    fetchConversations()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!activeConv) return
    const fetchMessages = async () => {
      try {
        const data = await getMessages(activeConv.id)
        setMessages(data)
      } catch {
        showToast('加载消息失败', 'error')
      }
    }
    fetchMessages()
  }, [activeConv]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: shouldReduceMotion ? 'auto' : 'smooth',
    })
  }, [messages, shouldReduceMotion])

  const handleSend = async () => {
    if (!input.trim() || !activeConv || sending) return
    setSending(true)
    const content = input.trim()
    setInput('')
    try {
      const msg = await sendMessage(activeConv.id, content)
      setMessages((prev) => [...prev, msg])
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
      await confirmTeam(activeConv.id)
      showToast('已确认组队意愿', 'success')
      setActiveConv((prev) => prev ? { ...prev, status: 'team_confirmed' } : null)
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
      const data = await getConversations()
      setConversations(data)
    } catch {
      showToast('操作失败', 'error')
    }
  }

  const openConversation = (conv: Conversation) => {
    setActiveConv(conv)
    setMobileChatOpen(true)
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
                  onClick={() => setMobileChatOpen(false)}
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
                  {activeConv.status === 'active' && (
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

            <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto bg-paper-warm/45 px-3 py-4 sm:px-5">
              <div className="space-y-3" aria-live="polite">
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
            ) : activeConv.status === 'team_confirmed' ? (
              <div className="shrink-0 border-t border-stone p-3">
                <div className="flex min-h-10 items-center justify-center gap-2 bg-green-50 px-3 text-sm font-medium text-campus-green">
                  <Lock aria-hidden="true" size={14} />
                  组队确认中
                </div>
              </div>
            ) : (
              <div className="shrink-0 border-t border-stone bg-paper p-3">
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
