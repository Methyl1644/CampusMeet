import { useState } from 'react'
import { X, Send } from 'lucide-react'
import type { Post } from '@shared/types'
import { createApplication } from '@/api/applications'
import { useAuthStore } from '@/store/authStore'
import { useToast } from './Toast'

interface ApplicationModalProps {
  post: Post
  onClose: () => void
  onSuccess: () => void
}

export default function ApplicationModal({ post, onClose, onSuccess }: ApplicationModalProps) {
  const [roleWanted, setRoleWanted] = useState('')
  const [experience, setExperience] = useState('')
  const [availableTime, setAvailableTime] = useState('')
  const [reason, setReason] = useState('')
  const [questions, setQuestions] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const { user } = useAuthStore()
  const { showToast } = useToast()

  const handleSubmit = async () => {
    if (!roleWanted) {
      showToast('请选择你想担任的角色', 'error')
      return
    }
    if (!experience.trim()) {
      showToast('请填写相关经验', 'error')
      return
    }
    if (!reason.trim()) {
      showToast('请填写加入原因', 'error')
      return
    }

    setSubmitting(true)
    try {
      await createApplication({
        post_id: post.id,
        role_wanted: roleWanted,
        experience: experience.trim(),
        available_time: availableTime.trim(),
        reason: reason.trim(),
        questions: questions.trim() ? [questions.trim()] : undefined,
      })
      showToast('申请已提交，等待回复', 'success')
      onSuccess()
      onClose()
    } catch {
      showToast('提交失败，请稍后重试', 'error')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 md:items-center" onClick={onClose}>
      <div
        className="w-full max-w-md rounded-t-2xl bg-white p-5 md:rounded-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* 头部 */}
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-base font-semibold text-gray-900">申请加入</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>

        {/* 帖子标题 */}
        <p className="mb-4 text-sm text-gray-500">{post.title}</p>

        {/* 角色选择 */}
        <div className="mb-4">
          <label className="mb-1.5 block text-sm font-medium text-gray-700">
            选择角色 <span className="text-red-500">*</span>
          </label>
          <div className="flex flex-wrap gap-2">
            {post.needed_roles.map((role) => (
              <button
                key={role}
                onClick={() => setRoleWanted(role)}
                className={`rounded-lg border px-3 py-1.5 text-sm transition-colors ${
                  roleWanted === role
                    ? 'border-primary-500 bg-primary-50 text-primary-600'
                    : 'border-gray-300 text-gray-600 hover:border-primary-300'
                }`}
              >
                {role}
              </button>
            ))}
          </div>
        </div>

        {/* 经验描述 */}
        <div className="mb-4">
          <label className="mb-1.5 block text-sm font-medium text-gray-700">
            相关经验 <span className="text-red-500">*</span>
          </label>
          <textarea
            value={experience}
            onChange={(e) => setExperience(e.target.value)}
            placeholder="描述你的相关经验，如项目经历、获奖情况等"
            rows={3}
            className="input-base resize-none"
          />
        </div>

        {/* 可投入时间 */}
        <div className="mb-4">
          <label className="mb-1.5 block text-sm font-medium text-gray-700">可投入时间</label>
          <input
            type="text"
            value={availableTime}
            onChange={(e) => setAvailableTime(e.target.value)}
            placeholder="如：每周6小时"
            className="input-base"
          />
        </div>

        {/* 加入原因 */}
        <div className="mb-4">
          <label className="mb-1.5 block text-sm font-medium text-gray-700">
            加入原因 <span className="text-red-500">*</span>
          </label>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="为什么想加入这个队伍？"
            rows={2}
            className="input-base resize-none"
          />
        </div>

        {/* 想问的问题 */}
        <div className="mb-5">
          <label className="mb-1.5 block text-sm font-medium text-gray-700">想问的问题（选填）</label>
          <textarea
            value={questions}
            onChange={(e) => setQuestions(e.target.value)}
            placeholder="有什么想问发布者的？"
            rows={2}
            className="input-base resize-none"
          />
        </div>

        {/* 操作按钮 */}
        <div className="flex gap-3">
          <button onClick={onClose} className="btn-secondary flex-1">
            取消
          </button>
          <button onClick={handleSubmit} disabled={submitting} className="btn-primary flex-1">
            <Send size={16} />
            {submitting ? '提交中...' : '提交申请'}
          </button>
        </div>

        {/* 当前用户提示 */}
        {user && (
          <p className="mt-3 text-center text-xs text-gray-400">
            以「{user.nickname}」身份申请
          </p>
        )}
      </div>
    </div>
  )
}
