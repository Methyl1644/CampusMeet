import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Send, RefreshCw, Check, Edit3, Sparkles } from 'lucide-react'
import { postDraft } from '@/api/agent'
import { createPost } from '@/api/posts'
import { useAuthStore } from '@/store/authStore'
import { useToast } from '@/components/Toast'
import { AIThinking } from '@/components/Loading'
import type { ChatMessage, PostDraft } from '@shared/types'

export default function Publish() {
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const { showToast } = useToast()

  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content: '你好！我是你的 AI 组队助手。告诉我你想参加什么活动，或者需要什么样的队友，我来帮你生成组队帖。\n\n例如：「我想参加美赛，还缺两个队友」',
      timestamp: new Date().toISOString(),
    },
  ])
  const [input, setInput] = useState('')
  const [draft, setDraft] = useState<PostDraft | null>(null)
  const [isComplete, setIsComplete] = useState(false)
  const [loading, setLoading] = useState(false)
  const [publishing, setPublishing] = useState(false)
  const [editingDraft, setEditingDraft] = useState(false)
  const [useManualForm, setUseManualForm] = useState(false)

  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, loading])

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
      })
      setDraft(res.draft)
      setIsComplete(res.is_complete)
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
      setUseManualForm(true)
      showToast('AI 服务异常，已切换到手动填写', 'error')
    } finally {
      setLoading(false)
    }
  }

  const handlePublish = async () => {
    if (!draft) return
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
    setIsComplete(false)
    setUseManualForm(false)
  }

  const updateDraftField = (field: keyof PostDraft, value: string | number | string[]) => {
    setDraft((prev) => (prev ? { ...prev, [field]: value } : null))
  }

  return (
    <div className="flex h-[calc(100vh-120px)] flex-col md:h-[calc(100vh-160px)]">
      {/* 顶部操作栏 */}
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles size={18} className="text-primary-600" />
          <h1 className="text-base font-semibold text-gray-900">AI 对话式发帖</h1>
        </div>
        <div className="flex gap-2">
          <button onClick={handleReset} className="btn-secondary text-xs">
            <RefreshCw size={14} />
            重新描述
          </button>
          {useManualForm && (
            <button onClick={() => setUseManualForm(false)} className="btn-secondary text-xs">
              回到对话
            </button>
          )}
        </div>
      </div>

      <div className="flex flex-1 gap-4 overflow-hidden">
        {/* 对话区 */}
        <div className="flex flex-1 flex-col overflow-hidden rounded-xl border border-gray-200 bg-white">
          <div ref={scrollRef} className="flex-1 overflow-y-auto p-4">
            <div className="space-y-3">
              {messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm ${
                      msg.role === 'user'
                        ? 'bg-primary-600 text-white'
                        : 'bg-gray-100 text-gray-700'
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                  </div>
                </div>
              ))}
              {loading && (
                <div className="flex justify-start">
                  <div className="rounded-2xl bg-gray-100 px-4 py-2.5">
                    <AIThinking />
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* 输入区 */}
          <div className="border-t border-gray-200 p-3">
            <div className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                placeholder="描述你的组队需求..."
                disabled={loading}
                className="input-base flex-1"
              />
              <button onClick={handleSend} disabled={loading || !input.trim()} className="btn-primary">
                <Send size={16} />
              </button>
            </div>
            <p className="mt-1.5 text-xs text-gray-400">
              AI 会自动追问缺失信息，你也可以随时在右侧编辑草稿
            </p>
          </div>
        </div>

        {/* 草稿预览区 */}
        <div className="hidden w-80 overflow-y-auto rounded-xl border border-gray-200 bg-white p-4 md:block">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-900">草稿预览</h3>
            {draft && (
              <button
                onClick={() => setEditingDraft(!editingDraft)}
                className="flex items-center gap-1 text-xs text-primary-600"
              >
                <Edit3 size={12} />
                {editingDraft ? '完成编辑' : '编辑'}
              </button>
            )}
          </div>

          {draft ? (
            <div className="space-y-3">
              <DraftField
                label="活动名称"
                value={draft.activity_name}
                editing={editingDraft}
                onChange={(v) => updateDraftField('activity_name', v)}
              />
              <DraftField
                label="目标人数"
                value={String(draft.target_members)}
                editing={editingDraft}
                onChange={(v) => updateDraftField('target_members', Number(v) || 1)}
              />
              <DraftField
                label="需要角色"
                value={draft.needed_roles.join('、')}
                editing={editingDraft}
                onChange={(v) => updateDraftField('needed_roles', v.split(/[、,，\s]+/).filter(Boolean))}
              />
              <DraftField
                label="每周投入"
                value={draft.weekly_hours}
                editing={editingDraft}
                onChange={(v) => updateDraftField('weekly_hours', v)}
              />
              <DraftField
                label="组队范围"
                value={draft.school_scope}
                editing={editingDraft}
                onChange={(v) => updateDraftField('school_scope', v)}
              />
              <DraftField
                label="截止日期"
                value={draft.deadline}
                editing={editingDraft}
                onChange={(v) => updateDraftField('deadline', v)}
              />

              {/* 发布按钮 */}
              <div className="pt-2">
                <button
                  onClick={handlePublish}
                  disabled={publishing || !isComplete}
                  className="btn-primary w-full"
                >
                  <Check size={16} />
                  {publishing ? '发布中...' : isComplete ? '确认发布' : '继续完善信息'}
                </button>
                {!isComplete && (
                  <p className="mt-1.5 text-center text-xs text-gray-400">
                    AI 正在帮你补全信息，完善后可发布
                  </p>
                )}
              </div>
            </div>
          ) : (
            <div className="py-8 text-center text-sm text-gray-400">
              <Sparkles size={32} className="mx-auto mb-2 text-gray-300" />
              <p>开始对话后，</p>
              <p>AI 会在这里生成草稿</p>
            </div>
          )}
        </div>
      </div>

      {/* 手机端草稿预览（底部弹出） */}
      {draft && (
        <div className="mt-2 rounded-xl border border-gray-200 bg-white p-3 md:hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-600">草稿：{draft.activity_name}</span>
            <button
              onClick={handlePublish}
              disabled={publishing}
              className="rounded-md bg-primary-600 px-3 py-1 text-xs text-white"
            >
              {isComplete ? '发布' : '完善中'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

/** 草稿字段组件 */
function DraftField({
  label,
  value,
  editing,
  onChange,
}: {
  label: string
  value: string
  editing: boolean
  onChange: (v: string) => void
}) {
  return (
    <div>
      <label className="mb-0.5 block text-xs font-medium text-gray-500">{label}</label>
      {editing ? (
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="input-base text-sm"
        />
      ) : (
        <p className="text-sm text-gray-800">{value || '—'}</p>
      )}
    </div>
  )
}
