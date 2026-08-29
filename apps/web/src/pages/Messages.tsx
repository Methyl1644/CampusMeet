import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Send, Shield, Handshake, XCircle, Lock } from 'lucide-react'
import { getConversations, getMessages, sendMessage, confirmTeam, closeConversation } from '@/api/messages'
import type { Conversation, Message } from '@shared/types'
import Loading from '@/components/Loading'
import EmptyState from '@/components/EmptyState'
import { useToast } from '@/components/Toast'

export default function Messages() {
  const navigate = useNavigate()
  const { showToast } = useToast()

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
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

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
    <div className="flex h-[calc(100vh-120px)] gap-3 md:h-[calc(100vh-160px)]">
      {/* 会话列表 */}
      <div className={`${mobileChatOpen ? 'hidden' : 'flex'} w-full flex-col overflow-hidden rounded-xl border border-gray-200 bg-white md:w-72 md:flex`}>
        <div className="border-b border-gray-200 p-3">
          <h2 className="text-sm font-semibold text-gray-900">消息</h2>
        </div>
        <div className="flex-1 overflow-y-auto">
          {conversations.length === 0 ? (
            <EmptyState title="暂无会话" description="接受申请后会自动创建会话" />
          ) : (
            conversations.map((conv) => (
              <button
                key={conv.id}
                onClick={() => openConversation(conv)}
                className={`flex w-full items-start gap-3 border-b border-gray-100 p-3 text-left transition-colors hover:bg-gray-50 ${
                  activeConv?.id === conv.id ? 'bg-primary-50' : ''
                }`}
              >
                <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-primary-100 text-sm font-medium text-primary-600">
                  {conv.other_user.nickname.charAt(0)}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between">
                    <span className="truncate text-sm font-medium text-gray-900">
                      {conv.other_user.nickname}
                    </span>
                    <span className="text-xs text-gray-400">{conv.last_message_at}</span>
                  </div>
                  <p className="truncate text-xs text-gray-500">{conv.last_message}</p>
                  {conv.unread_count > 0 && (
                    <span className="mt-0.5 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-xs text-white">
                      {conv.unread_count}
                    </span>
                  )}
                </div>
              </button>
            ))
          )}
        </div>
      </div>

      {/* 聊天界面 */}
      <div className={`${mobileChatOpen ? 'flex' : 'hidden'} flex-1 flex-col overflow-hidden rounded-xl border border-gray-200 bg-white md:flex`}>
        {activeConv ? (
          <>
            {/* 顶部操作栏 */}
            <div className="flex items-center justify-between border-b border-gray-200 p-3">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setMobileChatOpen(false)}
                  className="md:hidden"
                >
                  <ArrowLeft size={18} className="text-gray-500" />
                </button>
                <div>
                  <span className="text-sm font-medium text-gray-900">
                    {activeConv.other_user.nickname}
                  </span>
                  <p className="text-xs text-gray-400">{activeConv.post_title}</p>
                </div>
              </div>
              <div className="flex gap-2">
                {activeConv.status === 'active' && (
                  <button onClick={handleConfirmTeam} className="btn-secondary text-xs">
                    <Handshake size={14} />
                    愿意组队
                  </button>
                )}
                <button onClick={handleClose} className="btn-secondary text-xs text-red-500">
                  <XCircle size={14} />
                  结束
                </button>
              </div>
            </div>

            {/* 安全提示 */}
            <div className="flex items-center gap-2 bg-yellow-50 px-3 py-1.5">
              <Shield size={14} className="text-yellow-500" />
              <p className="text-xs text-yellow-700">
                请勿在聊天中交换联系方式，确认组队后将自动解锁
              </p>
            </div>

            {/* 消息列表 */}
            <div ref={scrollRef} className="flex-1 overflow-y-auto p-3">
              <div className="space-y-2">
                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex ${msg.is_mine ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[75%] rounded-2xl px-3 py-2 text-sm ${
                        msg.is_mine
                          ? 'bg-primary-600 text-white'
                          : 'bg-gray-100 text-gray-700'
                      }`}
                    >
                      {msg.content}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* 输入区 */}
            {activeConv.status === 'closed' ? (
              <div className="border-t border-gray-200 p-3 text-center text-sm text-gray-400">
                对话已结束
              </div>
            ) : activeConv.status === 'team_confirmed' ? (
              <div className="border-t border-gray-200 p-3">
                <div className="flex items-center justify-center gap-2 rounded-lg bg-green-50 py-2 text-sm text-green-600">
                  <Lock size={14} />
                  组队确认中，联系方式即将解锁
                </div>
              </div>
            ) : (
              <div className="border-t border-gray-200 p-3">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                    placeholder="输入消息..."
                    disabled={sending}
                    className="input-base flex-1"
                  />
                  <button onClick={handleSend} disabled={sending || !input.trim()} className="btn-primary">
                    <Send size={16} />
                  </button>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="flex flex-1 items-center justify-center">
            <EmptyState title="选择一个会话开始聊天" />
          </div>
        )}
      </div>
    </div>
  )
}
